"""Nordlys search-list extension.

Serializes the resolved skin configuration plus the station data into the
JSON payload the Nordlys front-end renders. The payload shape is the
Python <-> JS data contract, version 1 (see docs/data-contract.md and
src/lib/types.ts).
"""

import functools
import json
import logging
import os
import re
import time
from bisect import bisect_right

import weewx.almanac
import weewx.cheetahgenerator
import weewx.units
import weewx.xtypes
from weeutil.weeutil import (
    TimeSpan,
    archiveDaySpan,
    archiveMonthSpan,
    archiveWeekSpan,
    archiveYearSpan,
    genMonthSpans,
    genYearSpans,
    startOfDay,
)
from weeutil.config import accumulateLeaves as accumulate_leaves
from weewx.cheetahgenerator import SearchList

log = logging.getLogger(__name__)

CONTRACT_VERSION = 1

_TILE_TYPES = {
    'gauge', 'stat', 'chart', 'table', 'text',
    'climatology', 'celestial', 'forecast', 'reports',
}
_CHART_KINDS = {'line', 'area', 'bar', 'scatter', 'windrose', 'calendar'}
_TABLE_KINDS = {'stats', 'records'}
_THEME_MODES = {'auto', 'dark', 'light'}
# Tile types that render a single observation from `current`.
_OBS_TILE_TYPES = {'gauge', 'stat'}
# Tile types that reference an observation and so default `obs` from the
# section name. Other types (text, climatology, celestial, forecast,
# reports) ignore `obs` and must not inherit the section name.
_OBS_DEFAULTING_TILE_TYPES = {'gauge', 'stat', 'chart', 'table'}
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
    '24h': 86400,
    'week': 7 * 86400,
    'month': 30 * 86400,
    'year': 365 * 86400,
}
# Calendar-bound day spans, resolved via archiveDaySpan(days_ago=N).
# 'day' is calendar today (midnight -> now); 'yesterday' the prior day.
_CALENDAR_DAY_SPANS = {'day': 0, 'yesterday': 1}
# All spans a chart/records tile may reference.
_CHART_SPANS = set(_SPAN_SECONDS) | set(_CALENDAR_DAY_SPANS)
# Default aggregation interval per span (None = raw archive records).
_SPAN_AGG_INTERVAL = {
    '24h': None,
    'day': None,
    'yesterday': None,
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

# Stats tables use calendar-bound spans (like weewx $day/$week/$month).
_STATS_SPANS = {
    'day': lambda ts: archiveDaySpan(ts),
    'yesterday': lambda ts: archiveDaySpan(ts, days_ago=1),
    'week': archiveWeekSpan,
    'month': archiveMonthSpan,
    'year': archiveYearSpan,
}
# strftime formats for extreme times per stats span.
_STATS_TIME_FORMAT = {
    'day': '%H:%M',
    'yesterday': '%H:%M',
    'week': '%a %H:%M',
    'month': '%d %b',
    'year': '%d %b',
    'alltime': '%d %b %Y',
    'archive': '%d %b',
}

# Archive (SummaryBy) pages: the 'archive' span resolves to the page's
# own period, with these aggregation intervals.
_PERIOD_AGG_INTERVAL = {'week': 3600, 'month': 10800, 'year': 86400}
# Default filename patterns for archive pages and NOAA reports; must
# match the template names configured in skin.conf.
_ARCHIVE_WEEK_PAGE = 'week-%Y-%m-%d.html'
_ARCHIVE_MONTH_PAGE = 'month-%Y-%m.html'
_ARCHIVE_YEAR_PAGE = 'year-%Y.html'
_NOAA_MONTH_FILE = 'NOAA/NOAA-%Y-%m.txt'
_NOAA_YEAR_FILE = 'NOAA/NOAA-%Y.txt'
# Page-level period picker kinds.
_PICKER_KINDS = {'week', 'month', 'year'}

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
    tile_type = section.get('type', 'stat')
    tile = {'type': tile_type}
    obs = section.get('obs')
    if obs is None and tile_type in _OBS_DEFAULTING_TILE_TYPES:
        # Windrose charts plot wind speed/direction internally and
        # reference no named observation, so they must not inherit the
        # section name as an obs (it would look like an absent sensor).
        if not (tile_type == 'chart' and section.get('chart') == 'windrose'):
            obs = obs_key
    if obs is not None:
        tile['obs'] = obs
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
    if 'picker' in section:
        page['picker'] = section['picker']
    return page


def _theme_config(section):
    theme = {'mode': section.get('mode', 'auto')}
    if 'switcher' in section:
        theme['switcher'] = _coerce(section['switcher'])
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


def _all_obs(pages):
    """Every observation any tile references, in config order."""
    keys = []
    for tile in _tiles(pages):
        for obs in _obs_list(tile):
            if obs not in keys:
                keys.append(obs)
    return keys


def _forced_obs(pages):
    """Observations kept visible even when empty (tile always_show)."""
    forced = set()
    for tile in _tiles(pages):
        options = tile.get('options') or {}
        if options.get('always_show'):
            forced.update(_obs_list(tile))
    return forced


def _span_timespan(span, last_ts):
    """TimeSpan for a chart/records span anchored at the last record.

    Calendar-bound day spans ('day', 'yesterday') snap to local midnight;
    the rest ('24h', 'week', 'month', 'year') are rolling windows.
    """
    if span in _CALENDAR_DAY_SPANS:
        return archiveDaySpan(last_ts, days_ago=_CALENDAR_DAY_SPANS[span])
    if span in _SPAN_SECONDS:
        return TimeSpan(last_ts - _SPAN_SECONDS[span], last_ts)
    return None


def _is_period_stat(tile):
    """A stat tile with a span reads period stats, not current."""
    return tile.get('type') == 'stat' and bool(
        (tile.get('options') or {}).get('span')
    )


def _collect_obs(pages):
    """Observation keys needing current data, in config order."""
    keys = []
    for tile in _tiles(pages):
        if tile.get('type') == 'chart':
            continue
        if _is_period_stat(tile):
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
        if span not in _CHART_SPANS and span != 'archive':
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
    """{span: [obs, ...]} referenced by stats-table and period stat tiles."""
    needs = {}
    for tile in _tiles(pages):
        options = tile.get('options', {})
        tile_type = tile.get('type')
        if tile_type == 'table' and options.get('table', 'stats') == 'stats':
            span = options.get('span', 'month')
        elif _is_period_stat(tile):
            span = options['span']
        else:
            continue
        if span not in _STATS_SPANS and span not in ('alltime', 'archive'):
            continue
        span_obs = needs.setdefault(span, [])
        for obs in _obs_list(tile):
            if obs not in span_obs:
                span_obs.append(obs)
    return needs


def _collect_tile_types(pages):
    return {tile.get('type') for tile in _tiles(pages)}


_CELESTIAL_SECTIONS = {'sun', 'sunpath', 'moon', 'seasons', 'planets'}


def _celestial_sections(pages):
    """Celestial sections any tile references (the bare combo tile has
    none). Non-empty means the extended, ephem-only almanac is needed."""
    sections = set()
    for tile in _tiles(pages):
        if tile.get('type') == 'celestial':
            section = (tile.get('options') or {}).get('section')
            if section:
                sections.add(section)
    return sections


def _reports_stats_obs(pages):
    """The at-a-glance obs a reports tile lists per period (its `stats`)."""
    for tile in _tiles(pages):
        if tile.get('type') == 'reports':
            stats = (tile.get('options') or {}).get('stats')
            if stats:
                return stats if isinstance(stats, list) else [stats]
    return []


def _gen_week_spans(start_ts, stop_ts, week_start=6):
    """Yield weekly TimeSpans covering [start_ts, stop_ts], honoring the
    station's week_start (like weeutil's genMonthSpans for months)."""
    span = archiveWeekSpan(start_ts, startOfWeek=week_start)
    while span.start < stop_ts:
        yield span
        # Step just past the boundary so DST never lands us back in place.
        span = archiveWeekSpan(span.stop + 3600, startOfWeek=week_start)


def _detect_period(timespan, week_start=6):
    """'week'/'month'/'year' when the timespan is exactly a calendar
    period (i.e. an archive page is being generated), else None.

    Compared via the period containing the timespan's midpoint, so
    boundary conventions don't matter. Week is checked first; a week span
    is shorter than a month/year and never collides with them.
    """
    midpoint = (timespan.start + timespan.stop) // 2
    if timespan == archiveWeekSpan(midpoint, startOfWeek=week_start):
        return 'week'
    if timespan == archiveMonthSpan(midpoint):
        return 'month'
    if timespan == archiveYearSpan(midpoint):
        return 'year'
    return None


def _period_meta(period_kind, start_ts, week_start=6):
    """(id, label) for an archive period, matching the archives index."""
    start = time.localtime(start_ts)
    if period_kind == 'week':
        return time.strftime('%Y-%m-%d', start), _week_label(start, week_start)
    if period_kind == 'month':
        return time.strftime('%Y-%m', start), time.strftime('%B %Y', start)
    return time.strftime('%Y', start), time.strftime('%Y', start)


def _week_label(start_tt, week_start):
    """Monday-start weeks read as ISO week numbers; other starts, which
    have no standard numbering, read as 'Week of <date>'."""
    if week_start == 0:
        return time.strftime('Week %V, %G', start_tt)
    return time.strftime('Week of %d %b %Y', start_tt)


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
        picker = page.get('picker')
        if picker is not None and picker not in _PICKER_KINDS:
            warnings.append(
                f"page '{page_id}': picker '{picker}' is not one of "
                f"{', '.join(sorted(_PICKER_KINDS))}"
            )
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
    if obs and tile_type not in _OBS_DEFAULTING_TILE_TYPES:
        warnings.append(
            f"{where}: {tile_type} tile ignores obs '{obs[0]}'"
        )

    if tile_type == 'celestial' and options.get('section'):
        section = options['section']
        if section not in _CELESTIAL_SECTIONS:
            warnings.append(
                f"{where}: unknown celestial section '{section}' "
                f"(expected one of {', '.join(sorted(_CELESTIAL_SECTIONS))})"
            )

    # Period stat tiles read from stats[span]; validate the span.
    if tile_type == 'stat' and options.get('span'):
        span = options['span']
        if span not in _STATS_SPANS and span not in ('alltime', 'archive'):
            warnings.append(
                f"{where}: unknown stat span '{span}' (expected "
                f"{', '.join(sorted(_STATS_SPANS))}, alltime or archive)"
            )

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
            if span not in _CHART_SPANS and span != 'archive':
                warnings.append(
                    f"{where}: unknown span '{span}' "
                    f"(expected one of {', '.join(sorted(_CHART_SPANS))} or archive)"
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
            if span not in _STATS_SPANS and span not in ('alltime', 'archive'):
                warnings.append(
                    f"{where}: unknown stats span '{span}' "
                    f"(expected week, month, year, alltime or archive)"
                )
        elif table == 'records':
            span = options.get('span', 'day')
            if span not in _CHART_SPANS and span != 'archive':
                warnings.append(
                    f"{where}: unknown span '{span}' "
                    f"(expected one of {', '.join(sorted(_CHART_SPANS))} or archive)"
                )
    return warnings


def validate_climo_days(definitions):
    """Warnings for [[climatological_days]] definitions ({id: items})."""
    warnings = []
    for def_id, items in definitions.items():
        # A disabled definition (enable=false) is skipped at generation,
        # so don't nag about its (possibly stripped-down) config.
        if not items.get('enable', True):
            continue
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

        # The live pages define what the Climate year picker swaps; keep
        # them even when an archive page replaces config['pages'] below.
        live_pages = list(config['pages'])

        if 'live' in getattr(nordlys_dict, 'sections', []):
            live = _section_items(nordlys_dict['live'])
            if live.get('broker'):
                config['live'] = live

        # Archive pages: the timespan is exactly a calendar week/month/
        # year; render the [[archive]] layout for that period.
        week_start = getattr(stn_info, 'week_start', 6)
        period_kind = _detect_period(timespan, week_start)
        period = None
        if period_kind:
            sections = getattr(nordlys_dict, 'sections', [])
            if 'archive' not in sections:
                log.warning(
                    'Nordlys: archive page generated but [Nordlys] has no '
                    '[[archive]] layout section'
                )
                config['pages'] = []
            else:
                period_id, label = _period_meta(
                    period_kind, timespan.start, week_start
                )
                page = _page_config('archive', nordlys_dict['archive'])
                page['title'] = label
                config['pages'] = [page]
                period = {'kind': period_kind, 'id': period_id, 'label': label}

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
        series_needs, rose_needs, calendar_needs = _collect_chart_needs(pages)
        stats_needs = _collect_stats_needs(pages)
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        empty_obs = self._empty_obs(
            _all_obs(pages), _forced_obs(pages), db_manager
        )

        # Per-year climate slice (climate-<year>.json), generated for each
        # SummaryByYear timespan and swapped in by the Climate year picker.
        climate_slice = None
        if period_kind == 'year':
            climate_slice = self._climate_slice(
                TimeSpan(timespan.start, timespan.stop),
                live_pages, nordlys_dict, db_manager, empty_obs,
            )

        if period:
            # Everything is scoped to the page's own period; "now"-style
            # data (current, almanac, forecast, climatology) is omitted.
            period_span = TimeSpan(timespan.start, timespan.stop)
            span_timespans = {'archive': period_span}
            span_intervals = {'archive': _PERIOD_AGG_INTERVAL[period_kind]}
            stats_spans = {'archive': period_span}
            current = {}
            climatology = None
            almanac = None
            forecast = None
        else:
            span_timespans = self._chart_timespans(
                series_needs, rose_needs, last_ts
            )
            span_intervals = _SPAN_AGG_INTERVAL
            stats_spans = self._calendar_stats_spans(
                stats_needs, last_ts, db_manager
            )
            current = self._current_data(pages, db_lookup)
            climatology = self._climatology_data(
                nordlys_dict, tile_types, calendar_needs, db_lookup, empty_obs
            )
            almanac = (
                self._almanac_data(db_lookup, bool(_celestial_sections(pages)))
                if 'celestial' in tile_types
                else None
            )
            forecast = (
                self._forecast_data(db_lookup)
                if 'forecast' in tile_types
                else None
            )

        series = self._series_data(
            series_needs, db_manager, span_timespans, span_intervals
        )
        windrose = self._windrose_data(rose_needs, db_manager, span_timespans)
        stats = self._stats_data(stats_needs, db_manager, stats_spans)
        # The archives index feeds reports tiles and period pickers - the
        # latter on both live pages (page picker) and archive pages (whose
        # own picker is driven by the period they represent).
        needs_archives = (
            'reports' in tile_types
            or period is not None
            or any(page.get('picker') for page in pages)
        )
        archives = (
            self._archives_index(
                db_manager, week_start, _reports_stats_obs(pages)
            )
            if needs_archives
            else None
        )
        payload = {
            'meta': {
                'version': CONTRACT_VERSION,
                'skinVersion': skin_dict.get('SKIN_VERSION'),
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
            'emptyObs': empty_obs,
            'series': series,
            'windrose': windrose,
            'stats': stats,
            'climatology': climatology,
            'almanac': almanac,
            'forecast': forecast,
            'period': period,
            'archives': archives,
        }

        # Escape "</" so the payload is safe inside a <script> element.
        nordlys_json = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
        # Standalone per-year climate slice for climate-<year>.json.
        climate_json = (
            json.dumps(climate_slice, ensure_ascii=False)
            if climate_slice
            else ''
        )
        return [
            {
                'nordlys_json': nordlys_json,
                'nordlys_climate_json': climate_json,
                # For the server-rendered fallback markup in the template.
                'nordlys_current': current,
                # Skin theme mode for the no-flash <head> bootstrap.
                'nordlys_theme_mode': config.get('theme', {}).get('mode', 'auto'),
                # Optional user stylesheet (path relative to HTML_ROOT).
                'nordlys_user_css': nordlys_dict.get('user_css', ''),
            }
        ]

    # ------------------------------------------------------------------
    # empty observations (absent sensors)

    def _empty_obs(self, all_obs, forced, db_manager):
        """Observations with no meaningful data over the whole archive -
        absent sensors. `sum` observations (rain) count as empty when
        their total is zero; others when they have no non-null records.
        `forced` obs (a tile's always_show) are never reported empty.
        """
        first_ts = db_manager.firstGoodStamp()
        last_ts = db_manager.lastGoodStamp()
        if not first_ts or not last_ts:
            return []
        extent = TimeSpan(first_ts, last_ts)
        return [
            obs
            for obs in all_obs
            if obs not in forced
            and not self._obs_has_data(obs, extent, db_manager)
        ]

    @staticmethod
    def _obs_has_data(obs, extent, db_manager):
        try:
            if obs in _SUM_OBS:
                total = weewx.xtypes.get_aggregate(
                    obs, extent, 'sum', db_manager
                )
                return total[0] is not None and total[0] != 0
            count = weewx.xtypes.get_aggregate(
                obs, extent, 'count', db_manager
            )
            return bool(count[0])
        except (
            weewx.UnknownType,
            weewx.UnknownAggregation,
            weewx.CannotCalculate,
        ):
            return False

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
            avg = self._average(obs, day_span, db_manager, decimals)
            if avg is not None:
                entry['avg'] = avg

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

    def _average(self, obs, day_span, db_manager, decimals):
        try:
            value_vt = weewx.xtypes.get_aggregate(obs, day_span, 'avg', db_manager)
        except (weewx.UnknownType, weewx.UnknownAggregation, weewx.CannotCalculate):
            return None
        value = self.generator.converter.convert(value_vt)
        if value[0] is None:
            return None
        return self._round(value[0], decimals)

    # ------------------------------------------------------------------
    # chart series

    @staticmethod
    def _chart_timespans(series_needs, rose_needs, last_ts):
        """{span: TimeSpan} for every chart span any tile references."""
        if not last_ts:
            return {}
        spans = set(series_needs) | set(rose_needs)
        result = {}
        for span in spans:
            timespan = _span_timespan(span, last_ts)
            if timespan is not None:
                result[span] = timespan
        return result

    def _series_data(self, series_needs, db_manager, span_timespans, span_intervals):
        if not series_needs:
            return {}
        labels = self.generator.skin_dict.get('Labels', {}).get('Generic', {})

        result = {}
        for span, obs_keys in series_needs.items():
            timespan = span_timespans.get(span)
            if timespan is None:
                continue
            interval = span_intervals.get(span)
            span_data = {}
            for obs in obs_keys:
                try:
                    entry = self._series(
                        obs, interval, timespan, db_manager, labels
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

    def _series(self, obs, interval, timespan, db_manager, labels):
        aggregate = None
        if obs in _SUM_OBS:
            # Rain is summed into buckets: hourly at raw/hourly
            # resolution, daily beyond.
            aggregate = 'sum'
            interval = 3600 if not interval or interval <= 3600 else 86400
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

    @staticmethod
    def _calendar_stats_spans(stats_needs, last_ts, db_manager):
        """{span: TimeSpan} for calendar-bound stats spans."""
        if not last_ts:
            return {}
        spans = {}
        for span in stats_needs:
            if span == 'alltime':
                first_ts = db_manager.firstGoodStamp()
                if first_ts:
                    spans[span] = TimeSpan(startOfDay(first_ts), last_ts)
            elif span in _STATS_SPANS:
                spans[span] = _STATS_SPANS[span](last_ts)
        return spans

    def _stats_data(self, stats_needs, db_manager, stats_spans):
        if not stats_needs:
            return {}
        labels = self.generator.skin_dict.get('Labels', {}).get('Generic', {})

        result = {}
        for span, obs_keys in stats_needs.items():
            timespan = stats_spans.get(span)
            if timespan is None:
                continue
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
            # Wettest day of the span - but a zero total has no wettest
            # day, so skip the meaningless "max 0.0 (01 Jan)".
            if probe[0]:
                max_entry, _ = extreme('maxsum', 'maxsumtime')
                if max_entry:
                    entry['max'] = max_entry
        else:
            max_entry, _ = extreme('max', 'maxtime')
            avg = aggregate('avg')
            # A minimum adds no information for wind/rain-rate/UV/radiation
            # (a "lowest gust ever" is just noise), matching current obs.
            if obs not in _NO_MIN_OBS:
                min_entry, _ = extreme('min', 'mintime')
                if min_entry:
                    entry['min'] = min_entry
            if max_entry:
                entry['max'] = max_entry
            if avg[0] is not None:
                entry['avg'] = self._round(avg[0], decimals)
        return entry

    # ------------------------------------------------------------------
    # climatology

    def _climatology_data(
        self, nordlys_dict, tile_types, calendar_needs, db_lookup, empty_obs=()
    ):
        wants_days = 'climatology' in tile_types and 'climatological_days' in getattr(
            nordlys_dict, 'sections', []
        )
        if not wants_days and not calendar_needs:
            return None
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp()
        if not last_ts:
            return None

        # The main payload carries the current year, plus a lightweight
        # index of every year so the Climate year picker renders without a
        # fetch (past years are swapped in from climate-<year>.json).
        year_span = archiveYearSpan(last_ts)
        climatology = self._year_climatology(
            year_span, nordlys_dict, calendar_needs, db_manager, empty_obs,
            wants_days,
        ) or {}
        years = self._climate_years(db_manager)
        if years:
            climatology['years'] = years

        return climatology or None

    def _year_climatology(
        self, year_span, nordlys_dict, calendar_needs, db_manager,
        empty_obs, wants_days,
    ):
        """Climatological days + calendar heatmap scoped to one year."""
        climatology = {}
        if wants_days and 'climatological_days' in getattr(
            nordlys_dict, 'sections', []
        ):
            section = nordlys_dict['climatological_days']
            days = []
            for def_id in section.sections:
                definition = _section_items(section[def_id])
                if not definition.get('enable', True):
                    continue
                if definition.get('obs') in empty_obs:
                    continue
                entry = self._climo_day_count(
                    def_id, definition, year_span, db_manager
                )
                if entry:
                    days.append(entry)
            if days:
                climatology['days'] = days

        for options in calendar_needs:
            obs_list = options.get('obs') or ['outTemp']
            entry = self._calendar(obs_list[0], options, year_span, db_manager)
            if entry:
                climatology['calendar'] = entry
                break  # one calendar per payload for now
        return climatology or None

    @staticmethod
    def _climate_years(db_manager):
        """[{year, label}] newest first, with partial-year coverage in the
        label so a count over a partial year can't silently mislead."""
        first_ts = db_manager.firstGoodStamp()
        last_ts = db_manager.lastGoodStamp()
        if not first_ts or not last_ts:
            return []
        first_year = time.localtime(first_ts).tm_year
        last_year = time.localtime(last_ts).tm_year
        years = []
        for year in range(last_year, first_year - 1, -1):
            span = archiveYearSpan(int(time.mktime((year, 6, 15, 12, 0, 0, 0, 0, -1))))
            if last_ts < span.stop - 86400:
                label = f'{year} (so far)'
            elif first_ts > span.start:
                label = f'{year} (from {time.strftime("%b", time.localtime(first_ts))})'
            else:
                label = str(year)
            years.append({'year': str(year), 'label': label})
        return years

    def _climate_slice(
        self, year_span, live_pages, nordlys_dict, db_manager, empty_obs,
    ):
        """The per-year swap-in payload for climate-<year>.json: the
        year-scoped climatology and year stats the Climate page renders."""
        calendar_needs = _collect_chart_needs(live_pages)[2]
        climatology = self._year_climatology(
            year_span, nordlys_dict, calendar_needs, db_manager, empty_obs,
            wants_days='climatology' in _collect_tile_types(live_pages),
        )
        year_obs = _collect_stats_needs(live_pages).get('year')
        stats = (
            self._stats_data({'year': year_obs}, db_manager, {'year': year_span})
            if year_obs
            else {}
        )
        year = time.strftime('%Y', time.localtime(year_span.start))
        return {'year': year, 'climatology': climatology or {}, 'stats': stats}

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

    def _calendar(self, obs, options, timespan, db_manager):
        aggregate = options.get('aggregate', 'avg')
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

    def _almanac_data(self, db_lookup, wants_extras=False):
        db_manager = db_lookup()
        last_ts = db_manager.lastGoodStamp() or int(time.time())
        stn = self.generator.stn_info
        lat, lon = stn.latitude_f, stn.longitude_f
        try:
            almanac = weewx.almanac.Almanac(last_ts, lat, lon)
            sunrise = almanac.sunrise.raw
            sunset = almanac.sunset.raw
            entry = {
                'sunrise': self._clock(sunrise),
                'sunset': self._clock(sunset),
                'moon_phase': almanac.moon_phase,
                'moon_fullness': almanac.moon_fullness,
                'hasExtras': bool(almanac.hasExtras),
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
            north = lat >= 0
            entry['always_up'] = summer == north
            entry['always_down'] = not entry['always_up']

        # The Celestial-page sections (sun path, twilight, seasons,
        # planets, moon times) need pyephem; compute only when a sectioned
        # celestial tile asks for them.
        if wants_extras and entry['hasExtras']:
            try:
                entry.update(self._almanac_extras(last_ts, lat, lon))
            except Exception:
                pass
        return entry

    def _almanac_extras(self, ts, lat, lon):
        a = weewx.almanac.Almanac(ts, lat, lon)
        lt = time.localtime(ts)
        extras = {'sun_now': lt.tm_hour * 60 + lt.tm_min}
        for key, value in (
            ('transit', lambda: self._clock(a.sun.transit.raw)),
            ('sun_alt', lambda: round(a.sun.alt, 1)),
            ('sun_az', lambda: round(a.sun.az, 1)),
            ('moonrise', lambda: self._clock(a.moon.rise.raw)),
            ('moonset', lambda: self._clock(a.moon.set.raw)),
            ('next_full_moon', lambda: self._date(a.next_full_moon.raw)),
            ('next_new_moon', lambda: self._date(a.next_new_moon.raw)),
        ):
            try:
                extras[key] = value()
            except Exception:
                pass

        delta = self._day_length_delta(ts, lat, lon)
        if delta is not None:
            extras['day_length_delta'] = delta

        twilight = {}
        for name, depth in (
            ('civil', -6), ('nautical', -12), ('astronomical', -18)
        ):
            try:
                t = weewx.almanac.Almanac(
                    ts, lat, lon, horizon=depth, use_center=1
                )
                twilight[name] = [
                    self._clock(t.sun.rise.raw), self._clock(t.sun.set.raw)
                ]
            except Exception:
                twilight[name] = [None, None]
        extras['twilight'] = twilight
        extras['sun_path'] = self._sun_path(ts, lat, lon)
        extras['seasons'] = self._seasons(a, ts, lat)
        extras['planets'] = self._planets(a)
        return extras

    def _day_length_delta(self, ts, lat, lon):
        today = self._day_length(ts, lat, lon)
        yesterday = self._day_length(ts - 86400, lat, lon)
        if today is None or yesterday is None:
            return None
        return int(today - yesterday)

    @staticmethod
    def _day_length(ts, lat, lon):
        a = weewx.almanac.Almanac(ts, lat, lon)
        rise, set_ = a.sunrise.raw, a.sunset.raw
        if rise and set_ and set_ > rise:
            return set_ - rise
        return None

    @staticmethod
    def _sun_path(ts, lat, lon):
        """Solar altitude every 30 min through the local day, for the
        sun-path arc: [[minutes-from-midnight, altitude-deg], ...]."""
        day_start = startOfDay(ts)
        path = []
        for minutes in range(0, 24 * 60 + 1, 30):
            try:
                alt = weewx.almanac.Almanac(
                    day_start + minutes * 60, lat, lon
                ).sun.alt
                path.append([minutes, round(alt, 1)])
            except Exception:
                continue
        return path

    def _seasons(self, a, ts, lat):
        seasons = {}
        try:
            eq = a.next_equinox.raw
            seasons['equinox'] = {
                'date': self._date(eq), 'days': int((eq - ts) // 86400)
            }
        except Exception:
            pass
        try:
            sol = a.next_solstice.raw
            # June solstice is the year's longest day in the north (summer),
            # shortest in the south; December is the reverse.
            june = time.localtime(sol).tm_mon in (5, 6, 7)
            kind = 'summer' if june == (lat >= 0) else 'winter'
            seasons['solstice'] = {
                'date': self._date(sol),
                'days': int((sol - ts) // 86400),
                'kind': kind,
            }
        except Exception:
            pass
        return seasons

    def _planets(self, a):
        planets = []
        for name in ('Venus', 'Mars', 'Jupiter', 'Saturn'):
            body = getattr(a, name.lower(), None)
            if body is None:
                continue
            try:
                rise = self._clock(body.rise.raw)
                set_ = self._clock(body.set.raw)
            except Exception:
                rise = set_ = None
            if rise or set_:
                planets.append({'name': name, 'rise': rise, 'set': set_})
        return planets

    @staticmethod
    def _clock(ts):
        return time.strftime('%H:%M', time.localtime(ts)) if ts else None

    @staticmethod
    def _date(ts):
        return time.strftime('%d %b %Y', time.localtime(ts)) if ts else None

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

    def _windrose_data(self, rose_needs, db_manager, span_timespans):
        if not rose_needs:
            return {}

        result = {}
        for span, options in rose_needs.items():
            timespan = span_timespans.get(span)
            if timespan is None:
                continue
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

    # ------------------------------------------------------------------
    # archives index

    def _archives_index(self, db_manager, week_start=6, stats_obs=()):
        """Every week/month/year in the database, with archive-page (and
        NOAA, for months/years) links. Oldest first; the front-end orders
        newest-first where needed. Months/years carry at-a-glance mini
        stats (avg/total per configured obs) for the period browser."""
        first_ts = db_manager.firstGoodStamp()
        last_ts = db_manager.lastGoodStamp()
        if not first_ts or not last_ts:
            return None

        weeks = []
        for span in _gen_week_spans(first_ts, last_ts, week_start):
            start = time.localtime(span.start)
            weeks.append(
                {
                    'id': time.strftime('%Y-%m-%d', start),
                    'label': _week_label(start, week_start),
                    'page': time.strftime(_ARCHIVE_WEEK_PAGE, start),
                }
            )
        months = []
        for span in genMonthSpans(first_ts, last_ts):
            start = time.localtime(span.start)
            entry = {
                'id': time.strftime('%Y-%m', start),
                'label': time.strftime('%B %Y', start),
                'month': time.strftime('%b', start),
                'year': time.strftime('%Y', start),
                'page': time.strftime(_ARCHIVE_MONTH_PAGE, start),
                'noaa': time.strftime(_NOAA_MONTH_FILE, start),
            }
            self._attach_period_stats(entry, stats_obs, span, db_manager)
            months.append(entry)
        years = []
        for span in genYearSpans(first_ts, last_ts):
            start = time.localtime(span.start)
            entry = {
                'id': time.strftime('%Y', start),
                'label': time.strftime('%Y', start),
                'page': time.strftime(_ARCHIVE_YEAR_PAGE, start),
                'noaa': time.strftime(_NOAA_YEAR_FILE, start),
            }
            self._attach_period_stats(entry, stats_obs, span, db_manager)
            years.append(entry)
        return {'weeks': weeks, 'months': months, 'years': years}

    def _attach_period_stats(self, entry, stats_obs, span, db_manager):
        if not stats_obs:
            return
        converter = self.generator.converter
        formatter = self.generator.formatter
        stats = []
        for obs in stats_obs:
            aggregate = 'sum' if obs in _SUM_OBS else 'avg'
            try:
                vt = weewx.xtypes.get_aggregate(
                    obs, span, aggregate, db_manager
                )
            except (
                weewx.UnknownType,
                weewx.UnknownAggregation,
                weewx.CannotCalculate,
            ):
                continue
            value = converter.convert(vt)
            if value[0] is None:
                continue
            decimals = self._decimals(formatter, value[1])
            stats.append(
                {
                    'obs': obs,
                    'value': self._round(value[0], decimals),
                    'unit': (
                        formatter.get_label_string(value[1], plural=False) or ''
                    ).strip(),
                    'decimals': decimals,
                    'aggregate': aggregate,
                }
            )
        if stats:
            entry['stats'] = stats

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


class NordlysWeekGenerator(weewx.cheetahgenerator.CheetahGenerator):
    """Generates per-week archive pages (week-<start-date>.html).

    weewx's CheetahGenerator knows only SummaryByDay/Month/Year. This
    registers a weekly span generator so the inherited machinery - file
    naming from the period start, and staleness that regenerates only the
    current/missing weeks - treats the skin's [NordlysWeekGenerator]
    [[SummaryByWeek]] section like a built-in SummaryBy period. The
    NordlysSearchList then detects the week timespan and serializes the
    [[archive]] layout scoped to that week.
    """

    def run(self):
        base = weewx.cheetahgenerator.CheetahGenerator
        week_start = getattr(self.stn_info, 'week_start', 6)
        base.generator_dict['SummaryByWeek'] = functools.partial(
            _gen_week_spans, week_start=week_start
        )
        base.format_dict['SummaryByWeek'] = '%Y-%m-%d'
        self.outputted_dict.setdefault('SummaryByWeek', [])

        section_name = 'NordlysWeekGenerator'
        gen_dict = weewx.cheetahgenerator.deep_copy(self.skin_dict)
        if section_name not in gen_dict:
            return
        gen_dict[section_name]['summarize_by'] = 'None'
        self.init_extensions(gen_dict[section_name])
        self.generate(gen_dict[section_name], section_name, self.gen_ts)
        self.teardown()


class NordlysPageGenerator(weewx.cheetahgenerator.CheetahGenerator):
    """Emits one canonical HTML file per configured [Nordlys][[pages]]
    page (`<id>.html`, the first page also as `index.html`) from the
    shared page shell. Pages are config, so page files follow the config
    with no per-page template entries. The payload is identical across
    files; the front-end activates the page named by the filename.
    """

    def run(self):
        import Cheetah.Template

        section_name = 'NordlysPageGenerator'
        gen_dict = weewx.cheetahgenerator.deep_copy(self.skin_dict)
        if section_name not in gen_dict:
            return
        self.init_extensions(gen_dict[section_name])
        report_dict = accumulate_leaves(gen_dict[section_name])
        template, dest_dir, encoding, binding = self._prepGen(report_dict)

        db = self.db_binder.get_manager(binding)
        last_ts = db.lastGoodStamp()
        if not last_ts:
            self.teardown()
            return
        timespan = TimeSpan(db.firstGoodStamp(), last_ts)

        pages_section = self.skin_dict.get('Nordlys', {}).get('pages', {})
        page_ids = list(getattr(pages_section, 'sections', []))
        if not page_ids:
            self.teardown()
            return

        # Build the (expensive) shared search list once, then render the
        # shell per page with just the page context prepended.
        base_list = self._getSearchList(
            encoding, timespan, binding, section_name, template
        )
        for index, page_id in enumerate(page_ids):
            title = pages_section[page_id].get('title', page_id)
            filename = 'index.html' if index == 0 else f'{page_id}.html'
            page_ctx = {
                'nordlys_page': {'id': page_id, 'title': title, 'canonical': filename}
            }
            try:
                compiled = Cheetah.Template.Template(
                    file=template,
                    searchList=[page_ctx] + base_list,
                    filter='AssureUnicode',
                    filtersLib=weewx.cheetahgenerator,
                )
                html = compiled.respond().encode(encoding)
            except Exception as exception:
                log.error('Nordlys: page %s failed: %s', filename, exception)
                continue
            with open(os.path.join(dest_dir, filename), 'wb') as handle:
                handle.write(html)
        self.teardown()
