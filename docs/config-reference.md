# Nordlys configuration reference

Everything Nordlys shows - pages, layout, tiles, charts, thresholds,
theme, live updates - is configured in the `[Nordlys]` section of
`skin.conf`. No template or JavaScript edits are ever needed.

Any option can also be overridden per station from **weewx.conf**, in
the report's section, without touching the skin at all:

```ini
[StdReport]
    [[NordlysReport]]
        skin = Nordlys
        [[[Nordlys]]]
            site_name = My station
            [[[[theme]]]]
                mode = dark
```

weewx merges these over the skin's own `skin.conf`, so weewx.conf wins.
Invalid config never breaks generation: Nordlys skips what it cannot
render and logs a warning describing the problem and where it is.

A machine-readable schema of the resolved config lives in
[config.schema.json](config.schema.json).

## Top level

```ini
[Nordlys]
    site_name = Aldersundet weather   # display name; default: station location
    user_css = user.css               # optional extra stylesheet, see theming guide
```

## `[[theme]]`

```ini
    [[theme]]
        mode = auto        # auto | dark | light
        [[[dark]]]         # --nl-* token overrides for dark mode
            accent = "#3ddc97"
        [[[light]]]        # ... and for light mode
            bg = "#f6f9fc"
```

`auto` follows the visitor's system preference. Token names are the
`--nl-*` custom properties without the prefix - the full list with
defaults is in the [theming guide](theming.md).

## `[[live]]`

```ini
    [[live]]
        broker = wss://example.com:9001   # MQTT over WebSocket
        topic = weather/loop              # default: weather/loop
```

The topic must carry JSON loop packets keyed by weewx observation names.
Unit suffixes (`outTemp_C`) are stripped, and `dayRain` feeds the rain
tile. Values must be in the report's unit system. When configured, the
page header shows a live indicator and tiles update in place; the MQTT
client is only downloaded by browsers when `[[live]]` is present.

## `[[formats]]` - date/time formats

strftime patterns shared by the SLE and the front-end, so extreme times,
chart axes, the footer, and the records table all format the same way.
Defaults are 24-hour time and European dates with abbreviated months:

```ini
    [[formats]]
        time = %H:%M                 # day-span extremes, records, live
        date = %d %b                 # month/year extremes, chart date ticks
        date_year = %d %b %Y         # all-time extremes, footer date
        datetime = %d %b %Y, %H:%M   # footer "Generated"
        weekday_time = %a %H:%M      # week-span extremes, records rows
```

The front-end understands a strftime subset (`%H %M %S %d %m %b %a %Y
%I %p`), month/day names in English (i18n via lang files is a later
issue). These keys are separate from weewx's `[Units][[TimeFormats]]`,
which formats Cheetah `$...` tags (e.g. NOAA reports), not the payload.

## `[[seo]]` - search & social sharing

Every page ships a meta description and OpenGraph/Twitter cards
automatically. `og:url`, `og:image`, and `sitemap.xml` need an **absolute
site root**, resolved as: `[[seo]] base_url` -> weewx's
`[Station] station_url` -> none. With no base URL, those absolute-only
bits are skipped (descriptions + cards with a relative image still ship,
and `sitemap.xml` is empty).

```ini
    [[seo]]
        base_url = https://weather.example.com/nordlys
        description = Custom description for the whole site
        image = og-image.png     # social card, relative to the site root
        robots = true            # emit robots.txt + sitemap.xml (default)
```

- Descriptions are page-aware by default (per-page title, or
  `<period> archive` on archive pages); override with `description`.
- `robots = false` writes a `Disallow: /` robots.txt and an empty
  sitemap.
- A JSON-LD `WebSite` + `Place` (schema.org) block ships on every page.

## `[[climatological_days]]`

First-class day-counting definitions, rendered by `climatology` tiles:

```ini
    [[climatological_days]]
        span = year               # counting window (calendar year)
        [[[frost_days]]]
            label = Frost days
            obs = outTemp
            aggregate = min       # min | max | avg | sum (of the day)
            op = <                # < | <= | > | >=
            value = 0             # threshold, in report units
```

A day is counted when its daily `aggregate` of `obs` compares true
against `value`. The shipped defaults follow the Norwegian (MET)
conventions: frost (frostdøgn), ice (isdøgn), summer (sommerdager ≥ 20),
tropical days (tropedager ≥ 30), tropical nights (tropenetter), precip
(nedbørdøgn), growing (vekstdøgn) and storm days. Labels ship in English;
i18n is a future issue.

The `climatology` tile renders these as a matrix - one row per definition,
one column per month (Jan..Dec) plus a year total. Months outside the
station's archive coverage render blank rather than a misleading `0`. On
the Climate page a year picker (shown when the archive spans more than one
year) swaps the whole matrix, calendar, and year stats between years,
fetching past years from `climate-<year>.json`.

Note: with weewx daily summaries, `tropical_nights` counts the 24-hour
min ≥ 20 °C (*tropedøgn*); the strict *tropenatt* (min over 20:00-08:00)
is not expressible from daily summaries.

**Add / override / remove** - all from weewx.conf, no skin edits:

```ini
    [[[Nordlys]]]
        [[[[climatological_days]]]]
            [[[[[summer_days]]]]]        # override a threshold
                value = 25               # German/DWD summer day
            [[[[[ice_days]]]]]           # remove a shipped default
                enable = false
            [[[[[hot_days]]]]]           # add a new one
                label = Hot days
                obs = outTemp
                aggregate = max
                op = >=
                value = 28
```

weewx merges weewx.conf over skin.conf but cannot delete a section, so
removal is done with `enable = false` (the SLE skips disabled defs).

## `[[pages]]` - pages, rows, tiles

```ini
    [[pages]]
        [[[today]]]               # page id; order = nav order
            title = Today
            [[[[now]]]]           # a row
                title = Now       # optional row heading
                columns = 4       # max columns on wide screens
                [[[[[outTemp]]]]] # a tile; section name = default obs
                    type = gauge
                    ...
        [[[week]]]
            title = Week
            picker = week         # period dropdown: week | month | year
            ...
```

Rows collapse to 2 columns under 900 px and 1 column under 560 px.

Every page is emitted as a real, canonical HTML file - `index.html` for
the first page, `<id>.html` for the rest (`week.html`, `climate.html`, …)
- so pages are shareable, bookmarkable, and work with the browser's
back/forward. Nav links are real `<a href>` (they work with JavaScript
disabled, using each page's server-rendered fallback); with JS, clicks
navigate in place via the History API from the shared payload.

A page-level `picker` (`week`/`month`/`year`) adds a dropdown on the
first row to jump to any past week/month/year. Weeks are real pages
(`week-<start-date>.html`) generated by Nordlys's own week generator;
months/years by weewx's SummaryBy. The same picker appears on the
archive pages, with a "‹ Current" entry back to the live page.

### Tile types

| type | shows | needs |
|---|---|---|
| `gauge` | SVG arc gauge (or wind compass) | `obs` |
| `stat` | value + today min/max + trend | `obs` |
| `chart` | uPlot chart, wind rose, or calendar heatmap | `obs` (except windrose/calendar) |
| `table` | stats table or archive records table | `obs` list |
| `climatology` | per-month/per-year `[[climatological_days]]` matrix | - |
| `celestial` | sun/moon combo, or one almanac `section` | - |
| `forecast` | Zambretti pressure forecast | - |
| `reports` | links to all archive pages + NOAA reports | - |
| `history` | cross-year "on this day/month" records | `obs` list |
| `text` | a static text tile (`title`) | - |

Common tile keys: `type`, `obs` (one name, or a comma list for charts
and tables), `title` (defaults to the observation's label).

Observations with no data over the whole archive (absent sensors - e.g.
a station with no rain gauge, or `radiation` reporting nothing) are
treated as empty: their gauge/stat/chart tiles are hidden, their rows
dropped from stats/records tables, and "rain days"-style climatological
counts suppressed. This keeps the default skin sensible on any station.
Set `always_show = true` on a tile to keep it visible regardless (its
value then reads "-").

### Options by tile type

**gauge**

```ini
    min = -20            # gauge scale bounds (report units)
    max = 35
    style = compass      # wind-direction compass variant
    color = accent-2     # token/CSS color for the range band + now-marker
    cold_below = 0       # switch to --nl-cold below this value
    hot_above = 25       # switch to --nl-hot above this value
```

**stat** - `color`, `cold_below`, `hot_above` as above (colors the value).
With a `span` (`day`/`yesterday`/`week`/`month`/`year`/`alltime`/`archive`)
the tile becomes a **period** stat: the hero value is the period average
(the total for rain), the detail row shows the period min/max, and there
is no trend or live update. Without a span it shows current conditions.

**chart**

```ini
    chart = line         # line | area | bar | scatter | windrose | calendar
    span = day           # 24h | day | yesterday | week | month | year
    obs = outTemp, dewpoint     # one or many series
    overlay = rainRate          # optional 2nd-axis line (e.g. over rain bars)
    colors = accent, accent-3   # optional per-series colors
```

- Spans: `day` is calendar today (midnight -> now) and `yesterday` the
  previous calendar day; `24h` is a trailing 24-hour window (the old
  `day` behavior); `week`/`month`/`year` are rolling windows.
- Series are aggregated per span: raw (`24h`/`day`/`yesterday`), hourly
  avg (week), 3-hourly (month), daily (year). Rain is summed: hourly
  buckets on the day spans, daily beyond - pair it with `chart = bar`.
- A single-series `line` chart fills its area; charts with several series
  stay unfilled so they don't obscure each other. `area` forces a fill.
- `overlay` draws one more obs as a line on a second (right) axis - e.g.
  a `rainRate` line over `rain` bars. The overlay is bucket-averaged onto
  the base series' timestamps, so it lines up at every span.
- `windrose` extras: `bands = 2, 4, 6, 9, 12` (speed band upper bounds,
  report units) and `calm_below = 0.5`.
- `calendar` extras: `aggregate = avg` (`min`/`max`/`sum` of each day),
  colored between `--nl-cold` and `--nl-hot` over a rolling year.

**table**

```ini
    table = stats        # stats | records
    span = month         # stats: day | yesterday | week | month | year | alltime
                         # records: 24h | day | yesterday | week | month | year
    obs = outTemp, outHumidity, barometer, windSpeed, rain
```

`stats` shows min/avg/max with times (rain: total + wettest day).
`records` is a sortable, paginated table of raw archive records built
from the same series data the charts use.

**celestial**

```ini
    section = sunpath    # sun | sunpath | moon | seasons | planets
```

A bare `celestial` tile (no `section`) is the compact sun-and-moon combo
card. With a `section` it renders one detailed panel - the Celestial page
lays out all five. Everything beyond sunrise/sunset/phase (sun path,
twilight, moon and planet rise/set, seasons) needs the optional `ephem`
Python package; without it those panels show the basic data plus a hint.

**stats table extras**

```ini
    style = cards        # render the extremes as record cards (label,
                         # value, date) - e.g. all-time station records
```

`style = cards` on a `stats` table shows each obs's highest/lowest (rain:
wettest day) as record cards instead of a min/avg/max table.

**reports** - `stats = outTemp, rain` adds at-a-glance period stats
(average/total per obs) to each month/year in the period browser.

**history**

```ini
    span = day           # day | month  (historical window to compare)
    obs = outTemp, windGust, rain
```

Cross-year "on this day in history" records: for each obs, the record
high/low and mean over every matching day in the archive, tagged with the
year (and time, for `span = day`) it occurred. `span = month` compares the
whole current month across years instead. Sum obs (rain) report the
wettest day and no low; wind/rain-rate/UV/radiation carry no low either.
Like current conditions, history is not rendered on per-period archive
pages. Absent sensors are dropped.

## `[[archive]]` - per-period page layout

> Not to be confused with the `archive` **page** (`[[pages]][[[archive]]]`,
> the browser tab at `archive.html`). This `[[archive]]` section is the
> layout weewx reuses for every generated *per-period* page. Distinct
> config paths - they don't clash.

weewx generates one page per calendar month and year
(`month-YYYY-MM.html`, `year-YYYY.html`) plus NOAA text reports
(`NOAA/NOAA-*.txt`). The `[[archive]]` section defines the layout used
by *all* archive pages - same rows/tiles as a normal page, with
`span = archive` meaning "this page's own period":

```ini
    [[archive]]
        [[[charts]]]
            columns = 2
            [[[[temperature]]]]
                type = chart
                chart = line
                obs = outTemp, dewpoint
                span = archive
        [[[stats]]]
            [[[[stats_table]]]]
                type = table
                table = stats
                span = archive
                obs = outTemp, rain
```

Archive series are aggregated 3-hourly on month pages and daily on year
pages (rain per day on both). Current-conditions tiles (gauge/stat/
celestial/forecast) are not available on archive pages. A `reports` tile
on any normal page lists every generated period with links.

## `[Labels]`

```ini
[Labels]
    [[Generic]]
        outTemp = Outside temperature
        ...
```

Display names for observations, used by tiles, charts, and tables.

## Units

Nordlys uses the report's unit system (weewx converts everything before
serialization). Set it per report in weewx.conf, e.g.:

```ini
    [[NordlysReport]]
        unit_system = metricwx
```

**Pressure labeling.** Metric stations report pressure in `mbar`, but
Nordic / European convention - and nearly every weather site - shows the
numerically identical value as `hPa`. Nordlys therefore labels `mbar` as
`hPa` out of the box (see `[Units][[Labels]]` in `skin.conf`); no
`group_pressure` override is needed. To show real `mbar`, either change
that skin label back to `" mbar"`, or force a different pressure unit in
weewx.conf:

```ini
    [[NordlysReport]]
        [[[Units]]]
            [[[[Groups]]]]
                group_pressure = mmHg    # or inHg, mbar
```

All thresholds in skin.conf (`cold_below`, gauge `min`/`max`, wind-rose
`bands`, climatological `value`s) are read in report units - if you
switch unit system, revisit them.

## Regeneration

Nordlys generates the whole site every report cycle (there are no
write-once pages), so config and theme changes take effect on the next
cycle - or immediately with:

```sh
weectl report run --config /path/to/weewx.conf
```
