# Nordlys data contract

**Version 1** - the JSON payload the Python search-list extension
(`bin/user/nordlys`) produces and the front-end (`src/`) consumes.
TypeScript mirror: `src/lib/types.ts`. Dev fixtures: `fixtures/*.json`.

The payload is embedded in each generated page:

```html
<script id="nordlys-data" type="application/json">{ ... }</script>
<div id="nordlys-app"></div>
```

In dev, the script element instead carries `data-src="/fixtures/today.json"`
and the front-end fetches it.

## Shape

```jsonc
{
  "meta": {
    "version": 1,            // contract version; bump on breaking changes
    "generatedAt": 1784457000, // unix seconds, report generation time
    "station": {
      "name": "…",           // [Nordlys] site_name, or station location
      "location": "…",       // weewx station location
      "latitude": 66.401,    // decimal degrees
      "longitude": 13.121,
      "altitude": "6 meter"  // preformatted, report units
    }
  },

  "config": {                // resolved [Nordlys] section of skin.conf
    "theme": {
      "mode": "auto",        // auto | dark | light
      "dark":  { "accent": "#3ddc97", … },  // --nl-* overrides, no prefix
      "light": { … }
    },
    "pages": [
      {
        "id": "today",       // section name
        "title": "Today",
        "layout": [          // rows, in config order
          {
            "title": "Now",  // optional row heading
            "columns": 4,    // max columns on wide screens
            "tiles": [
              {
                "type": "gauge",   // gauge | stat | chart | table | text
                "obs": "outTemp",  // key into "current"
                "title": "…",      // optional; defaults to obs label
                "options": {
                  "min": -20, "max": 35,   // gauge bounds
                  "style": "compass",      // gauge variant
                  "color": "accent-2",     // --nl-* token name or literal CSS color
                  "cold_below": 0,         // semantic --nl-cold below this value
                  "hot_above": 25          // semantic --nl-hot above this value
                }
              }
            ]
          }
        ]
      }
    ]
  },

  "current": {               // one entry per obs referenced by any non-chart tile
    "outTemp": {
      "value": 13.6,         // report units, rounded to "decimals"; null if unknown
      "unit": "°C",          // display label, stripped
      "label": "Outside temperature",  // from [Labels][[Generic]]
      "decimals": 1,         // from the weewx format string for the unit
      "min": { "value": 9.8, "time": "04:37" },  // today's extreme (optional)
      "max": { "value": 15.2, "time": "13:05" },
      "trend": 0.4           // change over last 3 h, report units (optional)
    }
  },

  "series": {                // one entry per span/obs referenced by chart tiles
    "day": {                 // rolling window anchored at the last record:
                             // day 24h | week 7d | month 30d | year 365d
      "outTemp": {
        "unit": "°C",
        "label": "Outside temperature",
        "decimals": 1,
        "points": [[1784381700, 14.8], …],  // [unix s, value|null], oldest first
        "aggregate": "avg"   // avg | sum; absent for raw archive records
      }
    }
  },

  "windrose": {              // one entry per span referenced by windrose tiles
    "day": {
      "unit": "m/s",
      "bands": [2, 4, 6, 9, 12],  // upper bounds, report units; last band open
      "calm": 6.9,           // % of samples calm (below calm_below) or dirless
      "samples": 288,
      "sectors": [[…], …]    // 16 sectors (N first, clockwise), each
                             // bands+1 percentages of all samples
    }
  },

  "stats": {                 // per span/obs referenced by stats-table tiles;
    "week": {                // spans are calendar-bound (like $week/$month/
                             // $year) plus "alltime"
      "outTemp": {
        "label": "…", "unit": "°C", "decimals": 1,
        "min": { "value": 10.2, "time": "Sun 02:10" },
        "avg": 13.2,
        "max": { "value": 17.0, "time": "Sun 14:55" }
        // sum observations (rain) instead carry:
        // "sum": 12.4, "max": {…}   (the wettest day)
      }
    }
  },

  "climatology": {           // present when a climatology/calendar tile exists
    "days": [                // from [Nordlys][[climatological_days]]
      { "id": "frost_days", "label": "Frost days", "count": 12,
        "obs": "outTemp", "aggregate": "min", "op": "<", "value": 0,
        "unit": "°C" }
    ],
    "calendar": {            // from a chart=calendar tile; rolling year
      "obs": "outTemp", "label": "…", "aggregate": "avg", "unit": "°C",
      "days": [[1784412000, 13.2], …]   // [day start unix s, value|null]
    }
  },

  "almanac": {               // present when a celestial tile exists
    "sunrise": "02:49", "sunset": "23:33", "day_length": "20:44",
    // at polar latitudes rise/set may be null; then one of:
    "always_up": true,       // midnight sun
    "always_down": false,    // polar night
    "moon_phase": "waxing crescent (increasing to full)",
    "moon_fullness": 31      // percent illuminated
  },

  "forecast": {              // present when a forecast tile exists
    "code": "B",             // Zambretti letter
    "text": "Fine weather",
    "trend": "steady"        // barometer over 3 h: rising|steady|falling
  },

  "period": {                // archive (SummaryBy) pages only, else null
    "kind": "month",         // month | year
    "label": "July 2026"
  },

  "archives": {              // present when a reports tile exists
    "months": [ { "id": "2026-07", "label": "July 2026", "month": "Jul",
                  "year": "2026", "page": "month-2026-07.html",
                  "noaa": "NOAA/NOAA-2026-07.txt" } ],
    "years":  [ { "id": "2026", "label": "2026", "page": "year-2026.html",
                  "noaa": "NOAA/NOAA-2026.txt" } ]
  }
}
```

### Archive pages

On SummaryBy month/year pages the SLE swaps `config.pages` for a single
page built from `[Nordlys][[archive]]`, scoped to the page's period: the
`archive` span key in `series`/`stats`/`windrose` resolves to that
period (3-hourly aggregation for months, daily for years). `current`,
`climatology`, `almanac`, and `forecast` are omitted; `period` is set so
the front-end shows the archive header with a link back to the index.

## Semantics

- **Units**: all values are converted to the report's unit system by the
  SLE. The front-end never converts units; it only formats numbers using
  `decimals`.
- **`current` selection**: the SLE serializes exactly the observations
  referenced by tiles. A tile whose obs is missing from `current` renders
  a "no data" placeholder.
- **Day totals**: for `rain`, `value` is the day's running sum, not the
  last archive value.
- **Extremes**: omitted where meaningless (`min` for wind/rain-rate/UV/
  radiation; both for `rain` and `windDir`). Times are `HH:MM` local.
- **Trends**: currently `outTemp` and `barometer`, change over the last
  three hours.
- **Theme overrides**: token names are the `--nl-*` custom properties
  without the prefix (see `src/theme/tokens.css` for the full set).
- **Tile coloring**: `options.color` sets the value/arc color (token name
  or literal). `cold_below`/`hot_above` (report units) switch to the
  semantic `--nl-cold`/`--nl-hot` tokens when crossed; they win over
  `color`. Values are compared exclusively (a value exactly at the bound
  keeps the default color).
- **Unknown options**: tile options are passed through verbatim from
  skin.conf, so future tile types can add options without a contract
  bump; the front-end ignores options it does not know.
- **Series aggregation**: per-span defaults are raw (day), 1 h avg
  (week), 3 h avg (month), 1 d avg (year); rain is always summed
  (hourly buckets on the day span). All series in one chart tile share
  the span, so they align on the first series' timestamps.
- **Live updates**: `config.live` (from `[Nordlys][[live]]`) holds the
  MQTT-over-WebSocket `broker` URL and `topic` (default
  `weather/loop`). Messages are JSON loop packets keyed by weewx obs
  names; unit suffixes (`outTemp_C`) are stripped and `dayRain` maps to
  `rain`. Values must already be in the report's unit system. The
  front-end updates `current` values (and locally exceeded extremes)
  in place; series are not updated live.
- **Escaping**: the serialized JSON has `</` escaped as `<\/` so it is
  safe inside a `<script>` element; `JSON.parse` is unaffected.

## Versioning

`meta.version` is bumped only for breaking shape changes. Additive fields
are allowed within a version; the front-end must tolerate unknown fields.

- **Tables**: `table = stats` tiles read from `stats`; `table = records`
  tiles render straight from `series` (their obs are included in the
  series needs), joined on the first column's timestamps, sorted and
  paginated client-side.
- **Climatological days**: each definition in
  `[Nordlys][[climatological_days]]` counts days in the span whose daily
  aggregate (`min|max|avg|sum`, from the weewx daily summaries) compares
  true (`op`, exclusive `<`/`>` or inclusive variants) against `value`
  in report units.

## Planned (not yet in v1)

Per-period archive pages (SummaryBy*), NOAA text reports, PWA - later
milestones, with this document updated in lockstep.
