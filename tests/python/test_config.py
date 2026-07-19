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

import weewx  # noqa: E402
import weewx.xtypes  # noqa: E402

from nordlys import (  # noqa: E402
    NordlysSearchList,
    _all_obs,
    _coerce,
    _collect_chart_needs,
    _collect_obs,
    _collect_stats_needs,
    _forced_obs,
    _page_config,
    _theme_config,
    _tile_config,
    validate_climo_days,
    validate_config,
    zambretti,
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

    def test_non_obs_tile_does_not_inherit_section_name(self):
        for tile_type in ('forecast', 'celestial', 'climatology', 'reports', 'text'):
            config = section([f'[{tile_type}]', f'type = {tile_type}'])
            tile = _tile_config(tile_type, config[tile_type])
            self.assertEqual(tile, {'type': tile_type})
            self.assertNotIn('obs', tile)

    def test_non_obs_tile_keeps_explicit_obs(self):
        config = section(['[celestial]', 'type = celestial', 'obs = outTemp'])
        tile = _tile_config('celestial', config['celestial'])
        self.assertEqual(tile, {'type': 'celestial', 'obs': 'outTemp'})


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

    def test_chart_tiles_are_not_current_obs(self):
        pages = [
            {
                'layout': [
                    {
                        'tiles': [
                            {'type': 'stat', 'obs': 'outTemp'},
                            {
                                'type': 'chart',
                                'obs': ['barometer'],
                                'options': {'chart': 'line'},
                            },
                        ]
                    }
                ]
            }
        ]
        self.assertEqual(_collect_obs(pages), ['outTemp'])


class TestObsCollection(unittest.TestCase):
    def _pages(self, tiles):
        return [{'layout': [{'tiles': tiles}]}]

    def test_all_obs_includes_charts_deduped(self):
        pages = self._pages(
            [
                {'type': 'stat', 'obs': 'outTemp'},
                {'type': 'chart', 'obs': ['outTemp', 'dewpoint']},
                {'type': 'forecast'},
            ]
        )
        self.assertEqual(_all_obs(pages), ['outTemp', 'dewpoint'])

    def test_forced_obs_from_always_show(self):
        pages = self._pages(
            [
                {'type': 'stat', 'obs': 'rain', 'options': {'always_show': True}},
                {'type': 'stat', 'obs': 'outTemp'},
            ]
        )
        self.assertEqual(_forced_obs(pages), {'rain'})


class FakeDB:
    def __init__(self, first=1000, last=2000):
        self._first = first
        self._last = last

    def firstGoodStamp(self):
        return self._first

    def lastGoodStamp(self):
        return self._last


class TestEmptyObs(unittest.TestCase):
    def setUp(self):
        self.sle = NordlysSearchList.__new__(NordlysSearchList)
        self._orig = weewx.xtypes.get_aggregate

    def tearDown(self):
        weewx.xtypes.get_aggregate = self._orig

    def _patch(self, values):
        # values: {(obs, aggregate): scalar}
        def fake(obs, timespan, aggregate, db_manager, **kw):
            if (obs, aggregate) not in values:
                raise weewx.UnknownType(obs)
            return (values[(obs, aggregate)], 'unit', 'group')

        weewx.xtypes.get_aggregate = fake

    def test_no_data_obs_are_empty(self):
        self._patch(
            {
                ('outTemp', 'count'): 500,
                ('radiation', 'count'): 0,  # sensor reports nothing
                ('rain', 'sum'): 0,  # no rain gauge / all zero
            }
        )
        empty = self.sle._empty_obs(
            ['outTemp', 'radiation', 'rain'], set(), FakeDB()
        )
        self.assertEqual(empty, ['radiation', 'rain'])

    def test_rain_with_data_is_not_empty(self):
        self._patch({('rain', 'sum'): 12.4})
        self.assertEqual(self.sle._empty_obs(['rain'], set(), FakeDB()), [])

    def test_unknown_obs_is_empty(self):
        self._patch({})  # every lookup raises UnknownType
        self.assertEqual(
            self.sle._empty_obs(['missing'], set(), FakeDB()), ['missing']
        )

    def test_forced_obs_never_empty(self):
        self._patch({('rain', 'sum'): 0})
        self.assertEqual(self.sle._empty_obs(['rain'], {'rain'}, FakeDB()), [])

    def test_no_archive_returns_empty_list(self):
        self._patch({})
        empty = self.sle._empty_obs(['rain'], set(), FakeDB(first=None, last=None))
        self.assertEqual(empty, [])


class TestCollectChartNeeds(unittest.TestCase):
    def test_series_and_rose_split_by_span(self):
        pages = [
            {
                'layout': [
                    {
                        'tiles': [
                            {
                                'type': 'chart',
                                'obs': ['outTemp', 'dewpoint'],
                                'options': {'chart': 'line'},
                            },
                            {
                                'type': 'chart',
                                'obs': 'outTemp',
                                'options': {'chart': 'line', 'span': 'week'},
                            },
                            {
                                'type': 'chart',
                                'options': {'chart': 'windrose', 'bands': [2, 4]},
                            },
                            {'type': 'stat', 'obs': 'UV'},
                        ]
                    }
                ]
            }
        ]
        series, rose, calendar = _collect_chart_needs(pages)
        self.assertEqual(
            series, {'day': ['outTemp', 'dewpoint'], 'week': ['outTemp']}
        )
        self.assertEqual(list(rose), ['day'])
        self.assertEqual(rose['day']['bands'], [2, 4])
        self.assertEqual(calendar, [])

    def test_unknown_span_ignored(self):
        pages = [
            {
                'layout': [
                    {
                        'tiles': [
                            {
                                'type': 'chart',
                                'obs': 'outTemp',
                                'options': {'chart': 'line', 'span': 'decade'},
                            }
                        ]
                    }
                ]
            }
        ]
        self.assertEqual(_collect_chart_needs(pages), ({}, {}, []))


class TestCollectStatsNeeds(unittest.TestCase):
    def test_stats_tables_by_span(self):
        pages = [
            {
                'layout': [
                    {
                        'tiles': [
                            {
                                'type': 'table',
                                'obs': ['outTemp', 'rain'],
                                'options': {'table': 'stats', 'span': 'week'},
                            },
                            {
                                'type': 'table',
                                'obs': ['outTemp'],
                                'options': {'table': 'records', 'span': 'day'},
                            },
                            {'type': 'stat', 'obs': 'UV'},
                        ]
                    }
                ]
            }
        ]
        self.assertEqual(
            _collect_stats_needs(pages), {'week': ['outTemp', 'rain']}
        )

    def test_records_tables_feed_series_needs(self):
        pages = [
            {
                'layout': [
                    {
                        'tiles': [
                            {
                                'type': 'table',
                                'obs': ['outTemp', 'windDir'],
                                'options': {'table': 'records', 'span': 'day'},
                            }
                        ]
                    }
                ]
            }
        ]
        series, rose, calendar = _collect_chart_needs(pages)
        self.assertEqual(series, {'day': ['outTemp', 'windDir']})
        self.assertEqual(rose, {})
        self.assertEqual(calendar, [])


class TestZambretti(unittest.TestCase):
    def test_high_steady_pressure_is_settled(self):
        result = zambretti(1035.0, 0.2)
        self.assertEqual(result['trend'], 'steady')
        self.assertEqual(result['code'], 'A')

    def test_low_falling_pressure_is_stormy(self):
        result = zambretti(950.0, -3.0)
        self.assertEqual(result['trend'], 'falling')
        self.assertEqual(result['text'], 'Stormy, much rain')

    def test_trend_threshold(self):
        self.assertEqual(zambretti(1010.0, 1.0)['trend'], 'steady')
        self.assertEqual(zambretti(1010.0, 2.0)['trend'], 'rising')
        self.assertEqual(zambretti(1010.0, -2.0)['trend'], 'falling')

    def test_out_of_range_pressure_is_clamped(self):
        self.assertIsNotNone(zambretti(900.0, 0.0))
        self.assertIsNotNone(zambretti(1080.0, 0.0))
        self.assertIsNone(zambretti(None, 0.0))


class TestValidateConfig(unittest.TestCase):
    def _page(self, tiles):
        return {'pages': [{'id': 'p', 'title': 'P', 'layout': [{'tiles': tiles}]}]}

    def test_valid_config_has_no_warnings(self):
        config = self._page(
            [
                {'type': 'gauge', 'obs': 'outTemp'},
                {
                    'type': 'chart',
                    'obs': ['outTemp'],
                    'options': {'chart': 'line', 'span': 'week'},
                },
                {
                    'type': 'table',
                    'obs': ['outTemp'],
                    'options': {'table': 'stats', 'span': 'alltime'},
                },
                {'type': 'celestial'},
            ]
        )
        self.assertEqual(validate_config(config), [])

    def test_empty_pages_warns(self):
        self.assertTrue(validate_config({'pages': []}))

    def test_unknown_tile_type(self):
        warnings = validate_config(self._page([{'type': 'sparkline'}]))
        self.assertEqual(len(warnings), 1)
        self.assertIn("unknown tile type 'sparkline'", warnings[0])

    def test_gauge_without_obs(self):
        warnings = validate_config(self._page([{'type': 'gauge'}]))
        self.assertIn('gauge tile needs an obs', warnings[0])

    def test_obs_on_non_obs_tile_warns(self):
        warnings = validate_config(
            self._page([{'type': 'celestial', 'obs': 'outTemp'}])
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("celestial tile ignores obs 'outTemp'", warnings[0])

    def test_bad_chart_kind_and_span(self):
        warnings = validate_config(
            self._page(
                [
                    {'type': 'chart', 'obs': 'x', 'options': {'chart': 'pie'}},
                    {
                        'type': 'chart',
                        'obs': 'x',
                        'options': {'chart': 'line', 'span': 'decade'},
                    },
                ]
            )
        )
        self.assertEqual(len(warnings), 2)
        self.assertIn("unknown chart kind 'pie'", warnings[0])
        self.assertIn("unknown span 'decade'", warnings[1])

    def test_bad_theme_mode(self):
        warnings = validate_config(
            {'theme': {'mode': 'night'}, 'pages': [{'id': 'p', 'layout': []}]}
        )
        self.assertTrue(any('night' in w for w in warnings))

    def test_stats_table_span(self):
        warnings = validate_config(
            self._page(
                [
                    {
                        'type': 'table',
                        'obs': ['outTemp'],
                        'options': {'table': 'stats', 'span': 'day'},
                    }
                ]
            )
        )
        self.assertIn("unknown stats span 'day'", warnings[0])


class TestValidateClimoDays(unittest.TestCase):
    def test_valid_definition(self):
        definitions = {
            'frost': {'obs': 'outTemp', 'aggregate': 'min', 'op': '<', 'value': 0}
        }
        self.assertEqual(validate_climo_days(definitions), [])

    def test_bad_definition(self):
        definitions = {
            'broken': {'aggregate': 'median', 'op': '!=', 'value': 'cold'}
        }
        warnings = validate_climo_days(definitions)
        self.assertEqual(len(warnings), 4)  # obs, aggregate, op, value


if __name__ == '__main__':
    unittest.main()
