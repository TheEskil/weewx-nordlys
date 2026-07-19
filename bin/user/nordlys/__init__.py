"""Nordlys search-list extension.

Serializes the resolved skin configuration plus the station data into the
JSON payload the Nordlys front-end renders. The payload shape is the
Python <-> JS data contract, version 1 (see docs/data-contract.md and
src/lib/types.ts).
"""

import json
import logging
import re
import time
from bisect import bisect_right

import weewx.almanac
import weewx.units
import weewx.xtypes
from weeutil.weeutil import (
    TimeSpan,
    archiveDaySpan,
    archiveMonthSpan,
    archiveWeekSpan,
    archiveYearSpan,
    startOfDay,
)
from weewx.cheetahgenerator import SearchList

log = logging.getLogger(__name__)

CONTRACT_VERSION = 1

_TILE_TYPES = {
    'gauge', 'stat', 'chart', 'table', 'text',
    'climatology', 'celestial', 'forecast',
}
_CHART_KINDS = {'line', 'area', 'bar', 'scatter', 'windrose', 'calendar'}
_TABLE_KINDS = {'stats', 'records'}
_THEME_MODES = {'auto', 'dark', 'light'}
# Tile types that render a single observation from `current`.
_OBS_TILE_TYPES = {'gauge', 'stat'}
_CLIMO_AGGREGATES = {'min', 'max', 'avg', 'sum'}

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

# Stats tables use calendar-bound spans (like weewx $week/$month/$year).
_STATS_SPANS = {
    'week': archiveWeekSpan,
    'month': archiveMonthSpan,
    'year': archiveYearSpan,
}
# strftime formats for extreme times per stats span.
_STATS_TIME_FORMAT = {
    'week': '%a %H:%M',
    'month': '%d %b',
    'year': '%d %b',
    'alltime': '%d %b %Y',
}

# Zambretti forecaster (public-domain 1915 device mapping). The pressure
# range 947-1050 hPa is normalized to an index into the trend tables.
_ZAMBRETTI_TEXT = [
    'Settled fine', 'Fine weather', 'Becoming fine',
    'Fine, becoming less settled', 'Fine, possible showers',
    'Fairly fine, improving', 'Fairly fine, possible showers early',
    'Fairly fine, showery later', 'Showery early, improving',
    'Changeable, mending', 'Fairly fine, showers likely',
    'Rather unsettled, clearing later', 'Unsettled, probably improving',
    'Showery, bright intervals', 'Showery, becoming less settled',
    'Changeable, some rain', 'Unsettled, short fine intervals',
    'Unsettled, rain later', 'Unsettled, some rain',
    'Mostly very unsettled', 'Occasional rain, worsening',
    'Rain at times, very unsettled', 'Rain at frequent intervals',
    'Rain, very unsettled', 'Stormy, may improve', 'Stormy, much rain',
]
_ZAMBRETTI_RISING = [
    25, 25, 25, 24, 24, 19, 16, 12, 11, 9, 8, 6, 5, 2, 1, 1, 0, 0, 0, 0, 0, 0,
]
_ZAMBRETTI_STEADY = [
    25, 25, 25, 25, 25, 25, 23, 23, 22, 18, 15, 13, 10, 4, 1, 1, 0, 0, 0, 0, 0, 0,
]
_ZAMBRETTI_FALLING = [
    25, 25, 25, 25, 25, 25, 25, 25, 23, 23, 21, 20, 17, 14, 7, 3, 1, 1, 1, 0, 0, 0,
]
# Trend threshold in hPa over three hours.
_ZAMBRETTI_TREND_HPA = 1.6


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
    """(series, wind-rose, calendar) needs referenced by tiles.

    Series: {span: [obs, ...]} - from chart tiles and records tables
    (which render straight from series data).
    Wind rose: {span: options}. Calendar: [options, ...].
    """
    series_needs = {}
    rose_needs = {}
    calendar_needs = []
    for tile in _tiles(pages):
        options = tile.get('options', {})
        tile_type = tile.get('type')
        is_records_table = (
            tile_type == 'table' and options.get('table') == 'records'
        )
        if tile_type != 'chart' and not is_records_table:
            continue
        chart = options.get('chart')
        if chart == 'calendar':
            calendar_needs.append({**options, 'obs': _obs_list(tile)[0:1]})
            continue
        span = options.get('span', 'day')
        if span not in _SPAN_SECONDS:
            continue
        if chart == 'windrose':
            rose_needs.setdefault(span, options)
        else:
            span_obs = series_needs.setdefault(span, [])
            for obs in _obs_list(tile):
                if obs not in span_obs:
                    span_obs.append(obs)
    return series_needs, rose_needs, calendar_needs


def _collect_stats_needs(pages):
    """{span: [obs, ...]} referenced by stats-table tiles."""
    needs = {}
    for tile in _tiles(pages):
        if tile.get('type') != 'table':
            continue
        options = tile.get('options', {})
        if options.get('table', 'stats') != 'stats':
            continue
        span = options.get('span', 'month')
        if span not in _STATS_SPANS and span != 'alltime':
            continue
        span_obs = needs.setdefault(span, [])
        for obs in _obs_list(tile):
            if obs not in span_obs:
                span_obs.append(obs)
    return needs


def _collect_tile_types(pages):
    return {tile.get('type') for tile in _tiles(pages)}


def validate_config(config):
    """Human-readable warnings for suspicious [Nordlys] config.

    Purely advisory: generation always proceeds, skipping what it cannot
    render, but the warnings point at what (and where) to fix.
    """
    warnings = []
    mode = config.get('theme', {}).get('mode', 'auto')
    if mode not in _THEME_MODES:
        warnings.append(
            f"[[theme]] mode '{mode}' is not one of auto, dark, light"
        )

    pages = config.get('pages', [])
    if not pages:
        warnings.append('no pages configured under [[pages]]')
    for page in pages:
        page_id = page.get('id', '?')
        if not page.get('layout'):
            warnings.append(f"page '{page_id}' has no rows")
        for row in page.get('layout', []):
            if not row.get('tiles'):
                warnings.append(
                    f"page '{page_id}': row '{row.get('title', '?')}' has no tiles"
                )
            for tile in row.get('tiles', []):
                warnings.extend(_validate_tile(page_id, tile))
    return warnings


def _validate_tile(page_id, tile):
    warnings = []
    tile_type = tile.get('type')
    obs = _obs_list(tile)
    where = (
        f"page '{page_id}', tile "
        f"'{tile.get('title') or (obs[0] if obs else tile_type)}'"
    )

    if tile_type not in _TILE_TYPES:
        warnings.append(
            f"{where}: unknown tile type '{tile_type}' "
            f"(expected one of {', '.join(sorted(_TILE_TYPES))})"
        )
        return warnings

    options = tile.get('options', {})
    if tile_type in _OBS_TILE_TYPES and not obs:
        warnings.append(f'{where}: {tile_type} tile needs an obs')

    if tile_type == 'chart':
        chart = options.get('chart', 'line')
        if chart not in _CHART_KINDS:
            warnings.append(
                f"{where}: unknown chart kind '{chart}' "
                f"(expected one of {', '.join(sorted(_CHART_KINDS))})"
            )
        elif chart not in ('windrose', 'calendar'):
            if not obs:
                warnings.append(f'{where}: {chart} chart needs an obs')
            span = options.get('span', 'day')
            if span not in _SPAN_SECONDS:
                warnings.append(
                    f"{where}: unknown span '{span}' "
                    f"(expected one of {', '.join(_SPAN_SECONDS)})"
                )

    if tile_type == 'table':
        table = options.get('table', 'stats')
        if table not in _TABLE_KINDS:
            warnings.append(
                f"{where}: unknown table kind '{table}' "
                f"(expected stats or records)"
            )
        elif not obs:
            warnings.append(f'{where}: {table} table needs an obs list')
        elif table == 'stats':
            span = options.get('span', 'month')
            if span not in _STATS_SPANS and span != 'alltime':
                warnings.append(
                    f"{where}: unknown stats span '{span}' "
                    f"(expected week, month, year or alltime)"
                )
        elif table == 'records':
            span = options.get('span', 'day')
            if span not in _SPAN_SECONDS:
                warnings.append(
                    f"{where}: unknown span '{span}' "
                    f"(expected one of {', '.join(_SPAN_SECONDS)})"
                )
    return warnings


def validate_climo_days(definitions):
    """Warnings for [[climatological_days]] definitions ({id: items})."""
    warnings = []
    for def_id, items in definitions.items():
        where = f"[[climatological_days]] '{def_id}'"
        if not items.get('obs'):
            warnings.append(f'{where}: needs an obs')
        aggregate = items.get('aggregate', 'max')
        if aggregate not in _CLIMO_AGGREGATES:
            warnings.append(
                f"{where}: unknown aggregate '{aggregate}' "
                f"(expected min, max, avg or sum)"
            )
        op = items.get('op')
        if op not in ('<', '<=', '>', '>='):
            warnings.append(
                f"{where}: op must be one of <, <=, >, >= (got '{op}')"
            )
        value = items.get('value')
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            warnings.append(f"{where}: value must be a number (got '{value}')")
    return warnings


def zambretti(pressure_hpa, trend_hpa):
    """Zambretti forecast from sea-level pressure and its 3-hour change."""
    if pressure_hpa is None:
        return None
    index = int((pressure_hpa - 947.0) / 103.0 * 22)
    index = max(0, min(21, index))
    if trend_hpa is not None and trend_hpa >= _ZAMBRETTI_TREND_HPA:
        table, trend = _ZAMBRETTI_RISING, 'rising'
    elif trend_hpa is not None and trend_hpa <= -_ZAMBRETTI_TREND_HPA:
        table, trend = _ZAMBRETTI_FALLING, 'falling'
    else:
        table, trend = _ZAMBRETTI_STEADY, 'steady'
    entry = table[index]
    return {
        'code': chr(ord('A') + entry),
        'text': _ZAMBRETTI_TEXT[entry],
        'trend': trend,
    }


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

        for warning in validate_config(config):
            log.warning('Nordlys skin.conf: %s', warning)
        if 'climatological_days' in getattr(nordlys_dict, 'sections', []):
            section = nordlys_dict['climatological_days']
            definitions = {
                def_id: _section_items(section[def_id])
                for def_id in section.sections
            }
            for warning in validate_climo_days(definitions):
                log.warning('Nordlys skin.conf: %s', warning)

        pages = config['pages']
        tile_types = _collect_tile_types(pages)
        current = self._current_data(pages, db_lookup)
        series_needs, rose_needs, calendar_needs = _collect_chart_needs(pages)
        series = self._series_data(series_needs, db_lookup)
        windrose = self._windrose_data(rose_needs, db_lookup)
        stats = self._stats_data(_collect_stats_needs(pages), db_lookup)
        climatology = self._climatology_data(
            nordlys_dict, tile_types, calendar_needs, db_lookup
        )
        almanac = (
            self._almanac_data(db_lookup) if 'celestial' in tile_types else None
        )
        forecast = (
            self._forecast_data(db_lookup) if 'forecast' in tile_types else None
        )
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
            'stats': stats,
            'climatology': climatology,
            'almanac': almanac,
            'forecast': forecast,
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
            # Rain is summed into buckets: hourly on the day span,
            # daily beyond.
            aggregate = 'sum'
            interval = 3600 if span == 'day' else 86400
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
    # stats tables

    def _stats_data(self, stats_needs, db_lookup):
        if not stats_needs:
            return {}
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        if not last_ts:
            return {}
        labels = self.generator.skin_dict.get('Labels', {}).get('Generic', {})

        result = {}
        for span, obs_keys in stats_needs.items():
            if span == 'alltime':
                first_ts = db_manager.firstGoodStamp()
                if not first_ts:
                    continue
                timespan = TimeSpan(startOfDay(first_ts), last_ts)
            else:
                timespan = _STATS_SPANS[span](last_ts)
            span_data = {}
            for obs in obs_keys:
                try:
                    entry = self._stats_entry(
                        obs, span, timespan, db_manager, labels
                    )
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

    def _stats_entry(self, obs, span, timespan, db_manager, labels):
        converter = self.generator.converter
        formatter = self.generator.formatter
        time_format = _STATS_TIME_FORMAT[span]

        def aggregate(kind):
            return converter.convert(
                weewx.xtypes.get_aggregate(obs, timespan, kind, db_manager)
            )

        def extreme(kind, time_kind):
            value = aggregate(kind)
            if value[0] is None:
                return None, value[1]
            when = weewx.xtypes.get_aggregate(
                obs, timespan, time_kind, db_manager
            )
            result = {'value': self._round(value[0], decimals)}
            if when[0] is not None:
                result['time'] = time.strftime(
                    time_format, time.localtime(when[0])
                )
            return result, value[1]

        # Probe the unit/decimals from an aggregate that exists for the obs.
        probe = aggregate('sum' if obs in _SUM_OBS else 'min')
        decimals = self._decimals(formatter, probe[1])
        entry = {
            'label': labels.get(obs, obs),
            'unit': (
                formatter.get_label_string(probe[1], plural=False) or ''
            ).strip(),
            'decimals': decimals,
        }

        if obs in _SUM_OBS:
            entry['sum'] = self._round(probe[0], decimals)
            # Wettest day of the span.
            max_entry, _ = extreme('maxsum', 'maxsumtime')
            if max_entry:
                entry['max'] = max_entry
        else:
            min_entry, _ = extreme('min', 'mintime')
            max_entry, _ = extreme('max', 'maxtime')
            avg = aggregate('avg')
            if min_entry:
                entry['min'] = min_entry
            if max_entry:
                entry['max'] = max_entry
            if avg[0] is not None:
                entry['avg'] = self._round(avg[0], decimals)
        return entry

    # ------------------------------------------------------------------
    # climatology

    def _climatology_data(self, nordlys_dict, tile_types, calendar_needs, db_lookup):
        wants_days = 'climatology' in tile_types and 'climatological_days' in getattr(
            nordlys_dict, 'sections', []
        )
        if not wants_days and not calendar_needs:
            return None
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        if not last_ts:
            return None

        climatology = {}
        if wants_days:
            section = nordlys_dict['climatological_days']
            span = section.get('span', 'year')
            if span == 'year':
                timespan = archiveYearSpan(last_ts)
            else:
                timespan = TimeSpan(last_ts - _SPAN_SECONDS.get(span, 31536000), last_ts)
            days = []
            for def_id in section.sections:
                definition = _section_items(section[def_id])
                entry = self._climo_day_count(
                    def_id, definition, timespan, db_manager
                )
                if entry:
                    days.append(entry)
            if days:
                climatology['days'] = days

        for options in calendar_needs:
            obs_list = options.get('obs') or ['outTemp']
            entry = self._calendar(obs_list[0], options, last_ts, db_manager)
            if entry:
                climatology['calendar'] = entry
                break  # one calendar per payload for now

        return climatology or None

    _OPS = {
        '<': lambda a, b: a < b,
        '<=': lambda a, b: a <= b,
        '>': lambda a, b: a > b,
        '>=': lambda a, b: a >= b,
    }

    def _daily_rows(self, obs, timespan, db_manager):
        """(day start, min, max, sum, count) rows from the daily summaries."""
        sql = (
            f'SELECT dateTime, min, max, sum, count FROM archive_day_{obs} '
            'WHERE dateTime >= ? AND dateTime < ?'
        )
        return db_manager.genSql(sql, (timespan.start, timespan.stop))

    def _daily_value(self, row, aggregate):
        _, minimum, maximum, total, count = row
        if aggregate == 'min':
            return minimum
        if aggregate == 'max':
            return maximum
        if aggregate == 'sum':
            return total
        if aggregate == 'avg':
            return total / count if total is not None and count else None
        return None

    def _convert_db_value(self, value, obs, db_manager):
        if value is None:
            return None
        unit, group = weewx.units.getStandardUnitType(
            db_manager.std_unit_system, obs
        )
        return self.generator.converter.convert(
            weewx.units.ValueTuple(value, unit, group)
        )[0]

    def _climo_day_count(self, def_id, definition, timespan, db_manager):
        obs = definition.get('obs')
        op = self._OPS.get(definition.get('op'))
        threshold = definition.get('value')
        aggregate = definition.get('aggregate', 'max')
        if not obs or op is None or threshold is None:
            return None

        count = 0
        try:
            for row in self._daily_rows(obs, timespan, db_manager):
                value = self._convert_db_value(
                    self._daily_value(row, aggregate), obs, db_manager
                )
                if value is not None and op(value, threshold):
                    count += 1
        except Exception:
            return None

        unit, _ = weewx.units.getStandardUnitType(
            db_manager.std_unit_system, obs
        )
        target_unit = self.generator.converter.convert(
            weewx.units.ValueTuple(0.0, unit, weewx.units.obs_group_dict.get(obs))
        )[1]
        return {
            'id': def_id,
            'label': definition.get('label', def_id),
            'count': count,
            'obs': obs,
            'aggregate': aggregate,
            'op': definition.get('op'),
            'value': threshold,
            'unit': (
                self.generator.formatter.get_label_string(
                    target_unit, plural=False
                )
                or ''
            ).strip(),
        }

    def _calendar(self, obs, options, last_ts, db_manager):
        aggregate = options.get('aggregate', 'avg')
        timespan = TimeSpan(
            startOfDay(last_ts - 365 * 86400), last_ts
        )
        labels = self.generator.skin_dict.get('Labels', {}).get('Generic', {})

        days = []
        try:
            for row in self._daily_rows(obs, timespan, db_manager):
                value = self._convert_db_value(
                    self._daily_value(row, aggregate), obs, db_manager
                )
                days.append([row[0], self._round(value, 1)])
        except Exception:
            return None
        if not days:
            return None

        unit, _ = weewx.units.getStandardUnitType(
            db_manager.std_unit_system, obs
        )
        target_unit = self.generator.converter.convert(
            weewx.units.ValueTuple(0.0, unit, weewx.units.obs_group_dict.get(obs))
        )[1]
        return {
            'obs': obs,
            'label': labels.get(obs, obs),
            'aggregate': aggregate,
            'unit': (
                self.generator.formatter.get_label_string(
                    target_unit, plural=False
                )
                or ''
            ).strip(),
            'days': days,
        }

    # ------------------------------------------------------------------
    # almanac & forecast

    def _almanac_data(self, db_lookup):
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp() or int(time.time())
        stn = self.generator.stn_info
        try:
            almanac = weewx.almanac.Almanac(
                last_ts, stn.latitude_f, stn.longitude_f
            )
            sunrise = almanac.sunrise.raw
            sunset = almanac.sunset.raw
            entry = {
                'sunrise': self._clock(sunrise),
                'sunset': self._clock(sunset),
                'moon_phase': almanac.moon_phase,
                'moon_fullness': almanac.moon_fullness,
            }
        except Exception:
            return None
        if sunrise and sunset and sunset > sunrise:
            length = int(sunset - sunrise)
            entry['day_length'] = f'{length // 3600}:{length % 3600 // 60:02d}'
        elif not sunrise or not sunset:
            # Polar latitudes: no rise/set today. Northern-hemisphere
            # summer (Apr-Sep) means midnight sun, winter means polar
            # night; flipped south of the equator.
            month = time.localtime(last_ts).tm_mon
            summer = 4 <= month <= 9
            north = stn.latitude_f >= 0
            entry['always_up'] = summer == north
            entry['always_down'] = not entry['always_up']
        return entry

    @staticmethod
    def _clock(ts):
        return time.strftime('%H:%M', time.localtime(ts)) if ts else None

    def _forecast_data(self, db_lookup):
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        if not last_ts:
            return None
        record = db_manager.getRecord(last_ts)
        if not record or 'barometer' not in record:
            return None
        pressure = weewx.units.convert(
            weewx.units.as_value_tuple(record, 'barometer'), 'mbar'
        )[0]
        trend = None
        earlier = db_manager.getRecord(last_ts - _TREND_SECONDS, max_delta=1800)
        if earlier and earlier.get('barometer') is not None:
            then = weewx.units.convert(
                weewx.units.as_value_tuple(earlier, 'barometer'), 'mbar'
            )[0]
            if then is not None and pressure is not None:
                trend = pressure - then
        return zambretti(pressure, trend)

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
