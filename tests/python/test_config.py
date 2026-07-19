"""Unit tests for the Nordlys config serialization helpers.

Run with: .venv/bin/python -m unittest discover tests/python
"""

import os
import sys
import unittest

from configobj import ConfigObj

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'bin',
        'user',
    ),
)

from nordlys import (  # noqa: E402
    _coerce,
    _collect_obs,
    _page_config,
    _theme_config,
    _tile_config,
)


def section(lines):
    return ConfigObj(lines)


class TestCoerce(unittest.TestCase):
    def test_scalars(self):
        self.assertEqual(_coerce('-20'), -20)
        self.assertEqual(_coerce('3.5'), 3.5)
        self.assertIs(_coerce('true'), True)
        self.assertIs(_coerce('No'), False)
        self.assertEqual(_coerce('compass'), 'compass')

    def test_list(self):
        self.assertEqual(_coerce(['1', '2.5', 'x']), [1, 2.5, 'x'])


class TestTileConfig(unittest.TestCase):
    def test_defaults_obs_to_section_name(self):
        config = section(['[outTemp]', 'type = gauge', 'min = -20', 'max = 35'])
        tile = _tile_config('outTemp', config['outTemp'])
        self.assertEqual(
            tile,
            {
                'type': 'gauge',
                'obs': 'outTemp',
                'options': {'min': -20, 'max': 35},
            },
        )

    def test_type_defaults_to_stat(self):
        config = section(['[dewpoint]'])
        tile = _tile_config('dewpoint', config['dewpoint'])
        self.assertEqual(tile, {'type': 'stat', 'obs': 'dewpoint'})

    def test_explicit_obs_and_title(self):
        config = section(
            ['[gust]', 'type = stat', 'obs = windGust', 'title = Gusts']
        )
        tile = _tile_config('gust', config['gust'])
        self.assertEqual(
            tile, {'type': 'stat', 'obs': 'windGust', 'title': 'Gusts'}
        )


class TestPageConfig(unittest.TestCase):
    def test_rows_and_tiles_in_order(self):
        config = section(
            [
                '[today]',
                'title = Today',
                '[[now]]',
                'title = Now',
                'columns = 4',
                '[[[outTemp]]]',
                'type = gauge',
                '[[[windDir]]]',
                'type = gauge',
                'style = compass',
                '[[obs]]',
                '[[[dewpoint]]]',
            ]
        )
        page = _page_config('today', config['today'])
        self.assertEqual(page['id'], 'today')
        self.assertEqual(page['title'], 'Today')
        self.assertEqual(len(page['layout']), 2)
        now = page['layout'][0]
        self.assertEqual(now['title'], 'Now')
        self.assertEqual(now['columns'], 4)
        self.assertEqual(
            [t['obs'] for t in now['tiles']], ['outTemp', 'windDir']
        )
        self.assertEqual(
            now['tiles'][1]['options'], {'style': 'compass'}
        )


class TestThemeConfig(unittest.TestCase):
    def test_mode_and_token_overrides(self):
        config = section(
            [
                '[theme]',
                'mode = dark',
                '[[dark]]',
                'accent = "#00ff00"',
                '[[light]]',
            ]
        )
        theme = _theme_config(config['theme'])
        self.assertEqual(
            theme, {'mode': 'dark', 'dark': {'accent': '#00ff00'}}
        )

    def test_defaults(self):
        config = section(['[theme]'])
        self.assertEqual(_theme_config(config['theme']), {'mode': 'auto'})


class TestCollectObs(unittest.TestCase):
    def test_dedupes_preserving_order(self):
        pages = [
            {
                'layout': [
                    {'tiles': [{'obs': 'outTemp'}, {'obs': 'windDir'}]},
                    {'tiles': [{'obs': 'outTemp'}, {'type': 'text'}]},
                ]
            }
        ]
        self.assertEqual(_collect_obs(pages), ['outTemp', 'windDir'])


if __name__ == '__main__':
    unittest.main()
