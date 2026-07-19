"""Nordlys search-list extension.

Serializes the resolved skin configuration plus the station data into the
JSON payload the Nordlys front-end renders. The payload shape is the
Python <-> JS data contract, version 1 (see docs/data-contract.md and
src/lib/types.ts).

Milestone 2 will fill in `current` (and later `series`, `stats`,
`climatology`); this version ships the config + meta serialization so the
front-end contract is exercised end-to-end.
"""

import json
import time

from weewx.cheetahgenerator import SearchList

CONTRACT_VERSION = 1

# Keys on a page section that are settings, not layout rows.
_PAGE_SETTINGS = {'title'}
# Keys on a row section that are settings, not tiles.
_ROW_SETTINGS = {'title', 'columns'}
# Tile keys that stay at the top level of the tile object; everything
# else is passed through as tile options.
_TILE_SETTINGS = {'type', 'obs', 'title'}


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

        payload = {
            'meta': {
                'version': CONTRACT_VERSION,
                'generatedAt': int(time.time()),
                'station': {
                    'name': nordlys_dict.get('site_name', stn_info.location),
                    'location': stn_info.location,
                    'latitude': stn_info.latitude_f,
                    'longitude': stn_info.longitude_f,
                    'altitude': str(stn_info.altitude_vt[0]),
                },
            },
            'config': config,
            # Filled in by milestone 2 (current), then series/stats/climatology.
            'current': {},
        }

        # Escape "</" so the payload is safe inside a <script> element.
        nordlys_json = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
        return [{'nordlys_json': nordlys_json}]
