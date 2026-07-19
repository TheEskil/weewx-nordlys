"""Nordlys search-list extension.

Serializes the resolved skin configuration plus the station data into the
JSON payload the Nordlys front-end renders. The payload shape is the
Python <-> JS data contract, version 1 (see docs/data-contract.md and
src/lib/types.ts).
"""

import json
import re
import time

import weewx.units
import weewx.xtypes
from weeutil.weeutil import archiveDaySpan
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


def _collect_obs(pages):
    """All observation keys referenced by tiles, in config order."""
    keys = []
    for page in pages:
        for row in page['layout']:
            for tile in row['tiles']:
                obs = tile.get('obs')
                if obs and obs not in keys:
                    keys.append(obs)
    return keys


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

        current = self._current_data(config['pages'], db_lookup)
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
