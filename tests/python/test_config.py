"""Unit tests for the Nordlys config serialization helpers.

Run with: .venv/bin/python -m unittest discover tests/python
"""

import os
import sys
import time
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
from weeutil.weeutil import archiveMonthSpan, archiveWeekSpan  # noqa: E402

from nordlys import (  # noqa: E402
    NordlysSearchList,
    _all_obs,
    _celestial_sections,
    _coerce,
    _reports_stats_obs,
    _detect_period,
    _gen_week_spans,
    _period_meta,
    _span_timespan,
    _week_label,
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

    def test_windrose_chart_does_not_inherit_section_name(self):
        config = section(['[windrose]', 'type = chart', 'chart = windrose'])
        tile = _tile_config('windrose', config['windrose'])
        self.assertNotIn('obs', tile)

    def test_calendar_chart_keeps_section_name_obs(self):
        config = section(['[outTemp]', 'type = chart', 'chart = calendar'])
        tile = _tile_config('outTemp', config['outTemp'])
        self.assertEqual(tile['obs'], 'outTemp')


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


class TestAverage(unittest.TestCase):
    def setUp(self):
        self.sle = NordlysSearchList.__new__(NordlysSearchList)

        class Gen:
            class converter:
                @staticmethod
                def convert(vt):
                    return vt

        self.sle.generator = Gen()
        self._orig = weewx.xtypes.get_aggregate

    def tearDown(self):
        weewx.xtypes.get_aggregate = self._orig

    def _returns(self, value):
        weewx.xtypes.get_aggregate = lambda obs, ts, agg, db, **kw: (
            value,
            'unit',
            'group',
        )

    def test_rounds_to_decimals(self):
        self._returns(13.24)
        self.assertEqual(self.sle._average('outTemp', None, None, 1), 13.2)

    def test_none_value(self):
        self._returns(None)
        self.assertIsNone(self.sle._average('outTemp', None, None, 1))

    def test_unknown_aggregate(self):
        def raise_(*a, **kw):
            raise weewx.UnknownAggregation('avg')

        weewx.xtypes.get_aggregate = raise_
        self.assertIsNone(self.sle._average('foo', None, None, 1))


class TestSpanTimespan(unittest.TestCase):
    # 2026-07-15 12:00:00 local.
    TS = int(time.mktime((2026, 7, 15, 12, 0, 0, 0, 0, -1)))

    def test_24h_is_trailing_window(self):
        span = _span_timespan('24h', self.TS)
        self.assertEqual(span.stop - span.start, 86400)
        self.assertEqual(span.stop, self.TS)

    def test_day_is_calendar_today(self):
        span = _span_timespan('day', self.TS)
        midnight = int(time.mktime((2026, 7, 15, 0, 0, 0, 0, 0, -1)))
        self.assertEqual(span.start, midnight)

    def test_yesterday_is_previous_calendar_day(self):
        span = _span_timespan('yesterday', self.TS)
        start = int(time.mktime((2026, 7, 14, 0, 0, 0, 0, 0, -1)))
        stop = int(time.mktime((2026, 7, 15, 0, 0, 0, 0, 0, -1)))
        self.assertEqual((span.start, span.stop), (start, stop))

    def test_week_is_rolling(self):
        span = _span_timespan('week', self.TS)
        self.assertEqual(span.stop - span.start, 7 * 86400)

    def test_unknown_span(self):
        self.assertIsNone(_span_timespan('decade', self.TS))


class TestArchivePeriods(unittest.TestCase):
    def test_gen_week_spans_covers_range(self):
        start = int(time.mktime((2026, 7, 1, 0, 0, 0, 0, 0, -1)))
        stop = int(time.mktime((2026, 7, 20, 12, 0, 0, 0, 0, -1)))
        spans = list(_gen_week_spans(start, stop, week_start=6))
        self.assertGreaterEqual(len(spans), 3)
        # Contiguous, week-length, covering the whole range.
        for a, b in zip(spans, spans[1:]):
            self.assertEqual(a.stop, b.start)
        self.assertLessEqual(spans[0].start, start)
        self.assertGreater(spans[-1].stop, stop - 86400)

    def test_detect_period_week(self):
        mid = int(time.mktime((2026, 7, 15, 12, 0, 0, 0, 0, -1)))
        week = archiveWeekSpan(mid, startOfWeek=6)
        self.assertEqual(_detect_period(week, week_start=6), 'week')

    def test_detect_period_month_not_week(self):
        mid = int(time.mktime((2026, 7, 15, 12, 0, 0, 0, 0, -1)))
        month = archiveMonthSpan(mid)
        self.assertEqual(_detect_period(month, week_start=6), 'month')

    def test_period_meta_ids(self):
        ts = int(time.mktime((2026, 7, 13, 0, 0, 0, 0, 0, -1)))
        self.assertEqual(_period_meta('week', ts, 6)[0], '2026-07-13')
        self.assertEqual(_period_meta('month', ts, 6), ('2026-07', 'July 2026'))
        self.assertEqual(_period_meta('year', ts, 6), ('2026', '2026'))

    def test_week_label_monday_vs_other_start(self):
        mon = time.localtime(int(time.mktime((2026, 7, 13, 0, 0, 0, 0, 0, -1))))
        self.assertIn('Week', _week_label(mon, week_start=0))
        self.assertTrue(_week_label(mon, week_start=6).startswith('Week of'))


class TestClimateYears(unittest.TestCase):
    def test_years_newest_first_with_coverage(self):
        first = int(time.mktime((2024, 4, 10, 0, 0, 0, 0, 0, -1)))
        last = int(time.mktime((2026, 7, 19, 0, 0, 0, 0, 0, -1)))
        years = NordlysSearchList._climate_years(FakeDB(first, last))
        self.assertEqual([y['year'] for y in years], ['2026', '2025', '2024'])
        self.assertEqual(years[0]['label'], '2026 (so far)')  # current year
        self.assertEqual(years[1]['label'], '2025')  # full year
        self.assertTrue(years[2]['label'].startswith('2024 (from '))  # partial

    def test_no_archive(self):
        self.assertEqual(
            NordlysSearchList._climate_years(FakeDB(first=None, last=None)), []
        )


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

    def test_period_stat_tiles_feed_stats_needs(self):
        pages = [
            {
                'layout': [
                    {
                        'tiles': [
                            {'type': 'stat', 'obs': 'outTemp', 'options': {'span': 'year'}},
                            {'type': 'stat', 'obs': 'rain', 'options': {'span': 'year'}},
                            {'type': 'stat', 'obs': 'UV'},  # current, no span
                        ]
                    }
                ]
            }
        ]
        self.assertEqual(
            _collect_stats_needs(pages), {'year': ['outTemp', 'rain']}
        )

    def test_period_stat_tiles_excluded_from_current(self):
        pages = [
            {
                'layout': [
                    {
                        'tiles': [
                            {'type': 'stat', 'obs': 'outTemp', 'options': {'span': 'week'}},
                            {'type': 'stat', 'obs': 'UV'},
                        ]
                    }
                ]
            }
        ]
        self.assertEqual(_collect_obs(pages), ['UV'])

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

    def test_new_chart_spans_valid(self):
        for span in ('24h', 'day', 'yesterday', 'year'):
            config = self._page(
                [
                    {
                        'type': 'chart',
                        'obs': ['outTemp'],
                        'options': {'chart': 'line', 'span': span},
                    }
                ]
            )
            self.assertEqual(
                validate_config(config), [], f'{span} should be a valid chart span'
            )

    def test_picker_valid_and_invalid(self):
        good = {'pages': [{'id': 'week', 'title': 'Week', 'picker': 'week',
                           'layout': [{'tiles': [{'type': 'celestial'}]}]}]}
        self.assertEqual(validate_config(good), [])
        bad = {'pages': [{'id': 'week', 'title': 'Week', 'picker': 'fortnight',
                          'layout': [{'tiles': [{'type': 'celestial'}]}]}]}
        warnings = validate_config(bad)
        self.assertTrue(any("picker 'fortnight'" in w for w in warnings))

    def test_empty_pages_warns(self):
        self.assertTrue(validate_config({'pages': []}))

    def test_unknown_tile_type(self):
        warnings = validate_config(self._page([{'type': 'sparkline'}]))
        self.assertEqual(len(warnings), 1)
        self.assertIn("unknown tile type 'sparkline'", warnings[0])

    def test_gauge_without_obs(self):
        warnings = validate_config(self._page([{'type': 'gauge'}]))
        self.assertIn('gauge tile needs an obs', warnings[0])

    def test_period_stat_span_valid(self):
        for span in ('week', 'month', 'year', 'yesterday', 'alltime', 'archive'):
            warnings = validate_config(
                self._page([{'type': 'stat', 'obs': 'outTemp', 'options': {'span': span}}])
            )
            self.assertEqual(warnings, [], f'{span} should be a valid stat span')

    def test_period_stat_span_invalid(self):
        warnings = validate_config(
            self._page([{'type': 'stat', 'obs': 'outTemp', 'options': {'span': '24h'}}])
        )
        self.assertIn("unknown stat span '24h'", warnings[0])

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
                        'options': {'table': 'stats', 'span': 'decade'},
                    }
                ]
            )
        )
        self.assertIn("unknown stats span 'decade'", warnings[0])

    def test_calendar_day_stats_spans_valid(self):
        for span in ('day', 'yesterday'):
            warnings = validate_config(
                self._page(
                    [
                        {
                            'type': 'table',
                            'obs': ['outTemp'],
                            'options': {'table': 'stats', 'span': span},
                        }
                    ]
                )
            )
            self.assertEqual(warnings, [], f'{span} should be a valid stats span')


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

    def test_disabled_definition_is_not_validated(self):
        # A removed (enable=false) default may be stripped to nothing but
        # must not produce warnings.
        definitions = {'ice_days': {'enable': False}}
        self.assertEqual(validate_climo_days(definitions), [])


class TestCelestialSections(unittest.TestCase):
    def _pages(self, tiles):
        return [{'layout': [{'tiles': tiles}]}]

    def test_bare_celestial_has_no_sections(self):
        pages = self._pages([{'type': 'celestial'}])
        self.assertEqual(_celestial_sections(pages), set())

    def test_sections_collected(self):
        pages = self._pages(
            [
                {'type': 'celestial', 'options': {'section': 'sunpath'}},
                {'type': 'celestial', 'options': {'section': 'moon'}},
            ]
        )
        self.assertEqual(_celestial_sections(pages), {'sunpath', 'moon'})

    def test_valid_and_invalid_section(self):
        good = {'pages': [{'id': 'c', 'title': 'C', 'layout': [{'tiles': [
            {'type': 'celestial', 'options': {'section': 'planets'}}]}]}]}
        self.assertEqual(validate_config(good), [])
        bad = {'pages': [{'id': 'c', 'title': 'C', 'layout': [{'tiles': [
            {'type': 'celestial', 'options': {'section': 'comets'}}]}]}]}
        warnings = validate_config(bad)
        self.assertTrue(any("celestial section 'comets'" in w for w in warnings))


class TestReportsStatsObs(unittest.TestCase):
    def test_collects_stats_list(self):
        pages = [{'layout': [{'tiles': [
            {'type': 'reports', 'options': {'stats': ['outTemp', 'rain']}},
        ]}]}]
        self.assertEqual(_reports_stats_obs(pages), ['outTemp', 'rain'])

    def test_scalar_stats_wrapped(self):
        pages = [{'layout': [{'tiles': [
            {'type': 'reports', 'options': {'stats': 'outTemp'}},
        ]}]}]
        self.assertEqual(_reports_stats_obs(pages), ['outTemp'])

    def test_no_reports_or_no_stats(self):
        self.assertEqual(_reports_stats_obs([{'layout': [{'tiles': [
            {'type': 'reports'}]}]}]), [])
        self.assertEqual(_reports_stats_obs([{'layout': [{'tiles': [
            {'type': 'stat', 'obs': 'outTemp'}]}]}]), [])


if __name__ == '__main__':
    unittest.main()
