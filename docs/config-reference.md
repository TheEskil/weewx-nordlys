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
against `value`. The examples shipped in skin.conf cover frost, summer,
warm, rain, and storm days; add or change definitions freely.

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
```

Rows collapse to 2 columns under 900 px and 1 column under 560 px.

### Tile types

| type | shows | needs |
|---|---|---|
| `gauge` | SVG arc gauge (or wind compass) | `obs` |
| `stat` | value + today min/max + trend | `obs` |
| `chart` | uPlot chart, wind rose, or calendar heatmap | `obs` (except windrose/calendar) |
| `table` | stats table or archive records table | `obs` list |
| `climatology` | the `[[climatological_days]]` counts | - |
| `celestial` | sun rise/set, day length, moon phase | - |
| `forecast` | Zambretti pressure forecast | - |
| `reports` | links to all archive pages + NOAA reports | - |
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

**chart**

```ini
    chart = line         # line | area | bar | scatter | windrose | calendar
    span = day           # 24h | day | yesterday | week | month | year
    obs = outTemp, dewpoint     # one or many series
    colors = accent, accent-3   # optional per-series colors
```

- Spans: `day` is calendar today (midnight -> now) and `yesterday` the
  previous calendar day; `24h` is a trailing 24-hour window (the old
  `day` behavior); `week`/`month`/`year` are rolling windows.
- Series are aggregated per span: raw (`24h`/`day`/`yesterday`), hourly
  avg (week), 3-hourly (month), daily (year). Rain is summed: hourly
  buckets on the day spans, daily beyond - pair it with `chart = bar`.
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

## `[[archive]]` - archive pages

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
