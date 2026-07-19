"""Nordlys search-list extension.

Serializes the resolved skin configuration plus the station data into the
JSON payload the Nordlys front-end renders. The payload shape is the
Python <-> JS data contract, version 1 (see docs/data-contract.md and
src/lib/types.ts).
"""

import json
import re
import time
from bisect import bisect_right

import weewx.units
import weewx.xtypes
from weeutil.weeutil import TimeSpan, archiveDaySpan
from weewx.cheetahgenerator import SearchList

CONTRACT_VERSION = 1

# Keys on a row section that are settings, not tiles.
_ROW_SETTINGS = {'title', 'columns'}
# Tile keys that stay at the top level of the tile object; everything
# else is passed through as tile options.
_TILE_SETTINGS = {'type', 'obs', 'title'}

# Observations whose "current" value is the day's running total.
_DAY_SUM_OBS = {'rain'}
# Observations where a daily min (or any extreme) adds no information.
_NO_MIN_OBS = {'windSpeed', 'windGust', 'rainRate', 'UV', 'radiation'}
_NO_MINMAX_OBS = {'rain', 'windDir'}
# Observations that get a trend (change over the last three hours).
_TREND_OBS = {'outTemp', 'barometer'}
_TREND_SECONDS = 10800

# Rolling chart timespans, anchored at the last archive record.
_SPAN_SECONDS = {
    'day': 86400,
    'week': 7 * 86400,
    'month': 30 * 86400,
    'year': 365 * 86400,
}
# Default aggregation interval per span (None = raw archive records).
_SPAN_AGG_INTERVAL = {
    'day': None,
    'week': 3600,
    'month': 10800,
    'year': 86400,
}
# Observations aggregated by sum instead of average.
_SUM_OBS = {'rain'}

# Wind-rose defaults; bands are upper bounds in report units, the last
# band is open-ended. Overridable per tile in skin.conf.
_ROSE_BANDS = [2, 4, 6, 9, 12]
_ROSE_CALM_BELOW = 0.5


def _coerce(value):
    """ConfigObj yields strings; coerce scalars to JSON-friendly types."""
    if isinstance(value, list):
        return [_coerce(v) for v in value]
    if not isinstance(value, str):
        return value
    lowered = value.lower()
    if lowered in ('true', 'yes'):
        return True
    if lowered in ('false', 'no'):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _section_items(section):
    return {key: _coerce(section[key]) for key in section.scalars}


def _tile_config(obs_key, section):
    tile = {'type': section.get('type', 'stat'), 'obs': section.get('obs', obs_key)}
    if 'title' in section:
        tile['title'] = section['title']
    options = {
        key: value
        for key, value in _section_items(section).items()
        if key not in _TILE_SETTINGS
    }
    if options:
        tile['options'] = options
    return tile


def _page_config(page_id, section):
    layout = []
    for row_key in section.sections:
        row_section = section[row_key]
        row = {
            key: value
            for key, value in _section_items(row_section).items()
            if key in _ROW_SETTINGS
        }
        row['tiles'] = [
            _tile_config(tile_key, row_section[tile_key])
            for tile_key in row_section.sections
        ]
        layout.append(row)
    page = {'id': page_id, 'layout': layout}
    page['title'] = section.get('title', page_id)
    return page


def _theme_config(section):
    theme = {'mode': section.get('mode', 'auto')}
    for mode in ('dark', 'light'):
        if mode in section.sections:
            tokens = _section_items(section[mode])
            if tokens:
                theme[mode] = tokens
    return theme


def _tiles(pages):
    for page in pages:
        for row in page['layout']:
            for tile in row['tiles']:
                yield tile


def _obs_list(tile):
    obs = tile.get('obs')
    if obs is None:
        return []
    return obs if isinstance(obs, list) else [obs]


def _collect_obs(pages):
    """Observation keys needing current data, in config order."""
    keys = []
    for tile in _tiles(pages):
        if tile.get('type') == 'chart':
            continue
        for obs in _obs_list(tile):
            if obs not in keys:
                keys.append(obs)
    return keys


def _collect_chart_needs(pages):
    """(series needs, wind-rose needs) referenced by chart tiles.

    Returns ({span: [obs, ...]}, {span: options}).
    """
    series_needs = {}
    rose_needs = {}
    for tile in _tiles(pages):
        if tile.get('type') != 'chart':
            continue
        options = tile.get('options', {})
        span = options.get('span', 'day')
        if span not in _SPAN_SECONDS:
            continue
        if options.get('chart') == 'windrose':
            rose_needs.setdefault(span, options)
        else:
            span_obs = series_needs.setdefault(span, [])
            for obs in _obs_list(tile):
                if obs not in span_obs:
                    span_obs.append(obs)
    return series_needs, rose_needs


class NordlysSearchList(SearchList):
    """Provides $nordlys_json to the Nordlys templates."""

    def get_extension_list(self, timespan, db_lookup):
        skin_dict = self.generator.skin_dict
        nordlys_dict = skin_dict.get('Nordlys', {})
        stn_info = self.generator.stn_info

        config = {'pages': []}
        if 'theme' in getattr(nordlys_dict, 'sections', []):
            config['theme'] = _theme_config(nordlys_dict['theme'])
        if 'pages' in getattr(nordlys_dict, 'sections', []):
            pages_section = nordlys_dict['pages']
            config['pages'] = [
                _page_config(page_id, pages_section[page_id])
                for page_id in pages_section.sections
            ]

        if 'live' in getattr(nordlys_dict, 'sections', []):
            live = _section_items(nordlys_dict['live'])
            if live.get('broker'):
                config['live'] = live

        current = self._current_data(config['pages'], db_lookup)
        series_needs, rose_needs = _collect_chart_needs(config['pages'])
        series = self._series_data(series_needs, db_lookup)
        windrose = self._windrose_data(rose_needs, db_lookup)
        payload = {
            'meta': {
                'version': CONTRACT_VERSION,
                'generatedAt': int(time.time()),
                'station': {
                    'name': nordlys_dict.get('site_name', stn_info.location),
                    'location': stn_info.location,
                    'latitude': stn_info.latitude_f,
                    'longitude': stn_info.longitude_f,
                    'altitude': self._format_altitude(stn_info.altitude_vt),
                },
            },
            'config': config,
            'current': current,
            'series': series,
            'windrose': windrose,
        }

        # Escape "</" so the payload is safe inside a <script> element.
        nordlys_json = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
        return [
            {
                'nordlys_json': nordlys_json,
                # For the server-rendered fallback markup in the template.
                'nordlys_current': current,
                # Optional user stylesheet (path relative to HTML_ROOT).
                'nordlys_user_css': nordlys_dict.get('user_css', ''),
            }
        ]

    # ------------------------------------------------------------------
    # current data

    def _current_data(self, pages, db_lookup):
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        if not last_ts:
            return {}

        record = db_manager.getRecord(last_ts)
        trend_record = db_manager.getRecord(
            last_ts - _TREND_SECONDS, max_delta=1800
        )
        day_span = archiveDaySpan(last_ts)
        labels = self.generator.skin_dict.get('Labels', {}).get('Generic', {})

        current = {}
        for obs in _collect_obs(pages):
            try:
                entry = self._observation(
                    obs, record, trend_record, day_span, db_manager, labels
                )
            except (KeyError, weewx.UnknownType, weewx.CannotCalculate):
                continue
            if entry is not None:
                current[obs] = entry
        return current

    def _observation(self, obs, record, trend_record, day_span, db_manager, labels):
        converter = self.generator.converter
        formatter = self.generator.formatter

        if obs in _DAY_SUM_OBS:
            value_vt = weewx.xtypes.get_aggregate(obs, day_span, 'sum', db_manager)
        else:
            if obs not in record:
                return None
            value_vt = weewx.units.as_value_tuple(record, obs)
        value = converter.convert(value_vt)

        unit_label = (formatter.get_label_string(value[1], plural=False) or '').strip()
        decimals = self._decimals(formatter, value[1])

        entry = {
            'value': self._round(value[0], decimals),
            'unit': unit_label,
            'label': labels.get(obs, obs),
            'decimals': decimals,
        }

        if obs not in _NO_MINMAX_OBS:
            if obs not in _NO_MIN_OBS:
                extreme = self._extreme(obs, 'min', day_span, db_manager, decimals)
                if extreme:
                    entry['min'] = extreme
            extreme = self._extreme(obs, 'max', day_span, db_manager, decimals)
            if extreme:
                entry['max'] = extreme

        if obs in _TREND_OBS and trend_record and obs in trend_record:
            then = converter.convert(weewx.units.as_value_tuple(trend_record, obs))
            if value[0] is not None and then[0] is not None:
                entry['trend'] = self._round(value[0] - then[0], decimals)

        return entry

    def _extreme(self, obs, kind, day_span, db_manager, decimals):
        try:
            value_vt = weewx.xtypes.get_aggregate(obs, day_span, kind, db_manager)
            time_vt = weewx.xtypes.get_aggregate(
                obs, day_span, kind + 'time', db_manager
            )
        except (weewx.UnknownType, weewx.UnknownAggregation, weewx.CannotCalculate):
            return None
        value = self.generator.converter.convert(value_vt)
        if value[0] is None:
            return None
        extreme = {'value': self._round(value[0], decimals)}
        if time_vt[0] is not None:
            extreme['time'] = time.strftime('%H:%M', time.localtime(time_vt[0]))
        return extreme

    # ------------------------------------------------------------------
    # chart series

    def _series_data(self, series_needs, db_lookup):
        if not series_needs:
            return {}
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        if not last_ts:
            return {}
        labels = self.generator.skin_dict.get('Labels', {}).get('Generic', {})

        result = {}
        for span, obs_keys in series_needs.items():
            timespan = TimeSpan(last_ts - _SPAN_SECONDS[span], last_ts)
            span_data = {}
            for obs in obs_keys:
                try:
                    entry = self._series(obs, span, timespan, db_manager, labels)
                except (
                    weewx.UnknownType,
                    weewx.UnknownAggregation,
                    weewx.CannotCalculate,
                ):
                    continue
                if entry:
                    span_data[obs] = entry
            if span_data:
                result[span] = span_data
        return result

    def _series(self, obs, span, timespan, db_manager, labels):
        aggregate = None
        interval = _SPAN_AGG_INTERVAL[span]
        if obs in _SUM_OBS:
            # Rain is summed into buckets even on the raw span.
            aggregate, interval = 'sum', interval or 3600
        elif interval:
            aggregate = 'avg'

        _, stop_vt, data_vt = weewx.xtypes.get_series(
            obs,
            timespan,
            db_manager,
            aggregate_type=aggregate,
            aggregate_interval=interval,
        )
        data = self.generator.converter.convert(data_vt)
        formatter = self.generator.formatter
        unit_label = (formatter.get_label_string(data[1], plural=False) or '').strip()
        decimals = self._decimals(formatter, data[1])
        points = [
            [ts, self._round(value, decimals)]
            for ts, value in zip(stop_vt[0], data[0])
        ]
        entry = {
            'unit': unit_label,
            'label': labels.get(obs, obs),
            'decimals': decimals,
            'points': points,
        }
        if aggregate:
            entry['aggregate'] = aggregate
        return entry

    # ------------------------------------------------------------------
    # wind rose

    def _windrose_data(self, rose_needs, db_lookup):
        if not rose_needs:
            return {}
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        if not last_ts:
            return {}

        result = {}
        for span, options in rose_needs.items():
            timespan = TimeSpan(last_ts - _SPAN_SECONDS[span], last_ts)
            try:
                entry = self._windrose(timespan, db_manager, options)
            except (weewx.UnknownType, weewx.CannotCalculate):
                continue
            if entry:
                result[span] = entry
        return result

    def _windrose(self, timespan, db_manager, options):
        bands = options.get('bands', _ROSE_BANDS)
        if not isinstance(bands, list):
            bands = [bands]
        calm_below = options.get('calm_below', _ROSE_CALM_BELOW)

        _, _, speed_vt = weewx.xtypes.get_series('windSpeed', timespan, db_manager)
        _, _, dir_vt = weewx.xtypes.get_series('windDir', timespan, db_manager)
        speeds = self.generator.converter.convert(speed_vt)
        directions = dir_vt[0]

        sectors = [[0] * (len(bands) + 1) for _ in range(16)]
        calm = 0
        total = 0
        for speed, direction in zip(speeds[0], directions):
            if speed is None:
                continue
            total += 1
            if speed < calm_below or direction is None:
                calm += 1
                continue
            sector = int(round(direction / 22.5)) % 16
            sectors[sector][bisect_right(bands, speed)] += 1
        if not total:
            return None

        def pct(count):
            return round(100.0 * count / total, 1)

        unit_label = (
            self.generator.formatter.get_label_string(speeds[1], plural=False) or ''
        ).strip()
        return {
            'unit': unit_label,
            'bands': bands,
            'calm': pct(calm),
            'samples': total,
            'sectors': [[pct(count) for count in row] for row in sectors],
        }

    def _format_altitude(self, altitude_vt):
        converted = self.generator.converter.convert(altitude_vt)
        label = self.generator.formatter.get_label_string(
            converted[1], plural=False
        ) or ''
        return f'{converted[0]:g}{label}'

    @staticmethod
    def _decimals(formatter, unit):
        format_string = formatter.get_format_string(unit) or ''
        # Formats look like "%.1f" or "%03.0f"; extract the precision.
        match = re.search(r'%[\d#+0 -]*\.(\d+)f', format_string)
        return int(match.group(1)) if match else 1

    @staticmethod
    def _round(value, decimals):
        return round(value, decimals) if value is not None else None
