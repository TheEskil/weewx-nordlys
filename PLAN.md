# weewx-nordlys - design & build plan

## Context

**weewx-nordlys** is a modern weewx skin in the spirit of **weewx-wdc**, built clean-room, aiming
for **feature parity** with wdc, but architected so **end users reconfigure and re-theme the whole
dashboard from `skin.conf` - never touching code**. Name: *Nordlys* ("northern lights"), fitting a
station at Aldersundet, Lurøy (~66°N). The name dictates the visual identity: an aurora-derived
palette on a polar-night sky, and a **clean, minimal** presentation throughout.

Why not just keep wdc: wdc is powerful but its **React 18 + TypeScript + webpack + IBM Carbon +
Plotly.js + D3/Nivo** stack makes any visual change require forking the TS source and rebuilding.
Worse, Carbon renders key surfaces (the UI-shell header, the data tables) as **shadow-DOM web
components** whose colors external CSS and design tokens can't reach. Plotly is ~1 MB and hard to
theme cohesively, and the UI needs JS to render at all. Nordlys keeps **weewx as the data engine**
and replaces the presentation layer with a lean, token-themeable, **config-first** front-end.

Constraints driving the design: a Node/Vite build is acceptable · flexibility means **end-user
config, not code edits** · **clean-room** (wdc is a reference, not a source) · **feature-for-feature**
with wdc (minimalism is visual, not a scope cut) · charts are **uPlot + custom SVG** (decided below).

## Design principles

1. **Config is the interface.** Every user-facing choice - pages, layout/order, tiles, charts and
   their series/options, thresholds, units, colors, theme, live updates - is declared in `skin.conf`
   and requires no template/JS edits. This is the core differentiator from wdc.
2. **Token-based theming, no design-system lock-in.** All color/space/type/radius are CSS custom
   properties (`--nl-*`); user overrides via `skin.conf` `[[theme]]` and an optional `user.css`.
   **Dark ("polar night") is the design target**; light ("arctic daylight") is derived from it;
   the default follows `prefers-color-scheme`. **Never** put themeable surfaces in shadow DOM.
3. **Minimal by design.** Full wdc feature scope, but visually restrained: whitespace and hairlines
   instead of boxes, mostly monochrome surfaces, aurora accents reserved for data, state, and
   interactive elements. Details in "Design language" below.
4. **Progressive enhancement.** Cheetah server-renders the core values and tables (readable,
   indexable, works without JS); the JS layer enhances with interactive charts and live updates.
5. **Lean & fast.** Small, code-split, tree-shaken bundle; uPlot for weight/perf; hand-rolled SVG
   gauges (fully config/token-driven).
6. **Clean Python↔JS contract.** Python/Cheetah produce `{config, data}` JSON; the front-end renders
   it. The contract is documented so both sides evolve independently.
7. Accessible, responsive, PWA-capable.

## Design language: Nordlys

The name sets the scheme: aurora colors over a polar-night sky. All values below are the
**defaults of the `--nl-*` token set** - users can override any of them via `[[theme]]`/`user.css`.

### Palette - dark / "polar night" (hero theme)

| Token | Value | Role |
|---|---|---|
| `--nl-bg` | `#0B1220` | Page background - deep blue-black night sky |
| `--nl-surface` | `#111A2C` | Raised surfaces (tiles, cards) |
| `--nl-border` | `#1E2A40` | 1px hairlines |
| `--nl-text` | `#E8EEF7` | Primary text - ice white |
| `--nl-text-dim` | `#8FA3BF` | Secondary text, labels, units |
| `--nl-accent` | `#3DDC97` | Aurora green - primary accent |
| `--nl-accent-2` | `#4CC9F0` | Ice teal |
| `--nl-accent-3` | `#A78BFA` | Aurora violet |
| `--nl-accent-4` | `#E86BC1` | Magenta (rare red aurora) - use sparingly |
| `--nl-warm` | `#F0B860` | Muted amber - warm/warning semantics |

### Palette - light / "arctic daylight" (derived)

Snow `#F6F9FC` background, white `#FFFFFF` surfaces, `#D7E0EB` hairlines, deep blue-grey
`#17263B` text with `#5B6C82` secondary. Accents darken for contrast on white: green `#0E9F6E`,
teal `#0E7490`, violet `#7C3AED`, magenta `#C2338F`, amber `#B07817`. Body text always uses the
text tokens (AA 4.5:1); accents are held to ≥3:1 non-text contrast since they mark data, state,
and interactive elements - never running text.

### Chart & data colors

- **Series palette** (order): aurora green, ice teal, violet, magenta, amber, slate `#64748B`.
- **Semantic pairs** are separate tokens so data meaning isn't tied to brand colors:
  `--nl-cold`/`--nl-hot` (temperature gradients, climatogram), `--nl-ok`/`--nl-alert`
  (thresholds). Defaults draw from the palette (cold = ice teal, hot = amber→magenta ramp).

### Minimalism rules

- Generous whitespace on an **8px spacing scale**; a content max-width; alignment does the work.
- **Hairlines, not boxes**: 1px `--nl-border` separators; radius ~8px; **no drop shadows**
  (at most one barely-visible elevation tier for overlays).
- **One typeface**: system UI stack by default, optionally a self-hosted variable font - never a
  font CDN (breaks PWA/offline). **Tabular numerals** for all measurement values.
- Surfaces stay near-monochrome; accent colors appear only in data, state, and interaction.
- **Charts**: thin lines (1.5px), sparse muted gridlines, no legends where a label will do, no
  chart junk. **Gauges**: thin SVG arc strokes, numeric value dominant.

## Architecture

weewx's ReportEngine always drives generation (CheetahGenerator, CopyGenerator, SummaryBy*, ToDate,
NOAA). Nordlys layers on top:

- **Data + config layer - Python search-list extensions (SLE) + Cheetah.** Clean-room SLE classes
  (e.g. `WeatherData`, `Series`, `Stats`, `Climatology`, `Tables`, `Celestial`, `Forecast`) compute
  aggregates/series and, crucially, **serialize the resolved `skin.conf` config + the data to JSON**.
  Cheetah templates emit a thin semantic HTML shell per page (server-rendered current values + tables
  for progressive enhancement) plus the JSON payload and mount points.
- **Front-end - Vite + Svelte, as a config-driven renderer.** Reads `{config, data}`, renders
  gauges/stat-tiles/charts/tables/tabs/nav per the config. Themed entirely by CSS tokens.
  Live updates via MQTT. Service worker for PWA/offline.
- **Build.** Vite → hashed, code-split assets, output into `skins/Nordlys/dist/`, shipped by weewx
  `copy_once`. The framework is an implementation detail invisible to end users (who only touch
  `skin.conf`).

### Front-end framework - decision: Svelte

Svelte compiles away to small vanilla JS with no runtime framework cost - the best fit for a lean,
live-updating, config-driven dashboard. The JSON data contract keeps the front-end swappable if
that ever changes.

## The config model (the flexibility win)

`skin.conf` (parsed by the SLE and serialized to JSON) is the primary UX. Sketch:

```
[Nordlys]
    [[theme]]              # --nl-* token overrides, per light/dark
        mode   = auto      # auto | dark | light
        [[[dark]]]
            bg      = "#0B1220"
            accent  = "#3DDC97"   # aurora green
            ...                   # any token; unset = Nordlys default
        [[[light]]]
            ...
    [[units]]              # unit + format per obs group (reuse weewx unit system)
    [[live]]               # MQTT broker/topic for live updates (optional)
    [[pages]]
        [[[today]]]
            [[[[layout]]]] # ordered rows of tiles; responsive columns
                [[[[[tile]]]]]
                    type   = gauge | stat | chart | table | text
                    obs    = outTemp            # one or many series
                    chart  = line|area|bar|windrose|scatter|calendar
                    options / thresholds / colors ...
    [[climatological_days]]  # thresholds + labels as FIRST-CLASS config
```

A documented JSON Schema mirrors this. Users edit `skin.conf` → re-run reports → new layout/theme,
no code touched. This makes first-class the exact things that are painful to change in wdc (tile
colors, gauge colors, climatological thresholds/labels, chart palettes).

## Charts - decision: uPlot + custom SVG

- **uPlot** (~40 KB, canvas) renders all time-series - the fastest option for dense archive data,
  styled via the `--nl-*` tokens.
- **Hand-rolled SVG** covers what uPlot doesn't: gauges, the polar **wind-rose**, and the
  **calendar-heatmap** climatogram - fully config/token-driven, matching the minimal aesthetic.

Considered alternative: Apache ECharts (one lib for everything) - rejected for weight (~300 KB+
even tree-shaken) and because its JSON-theme styling is less directly token-driven than owning
the SVG.

## Feature-parity checklist (wdc → nordlys)

- Current conditions **gauges** (temp, barometer, wind speed, wind direction)
- **Stat tiles** for all observations (value, today min/max, trend, optional value-colored)
- **Charts:** temp/dewpoint, humidity, barometer, windchill/heatindex, wind speed/gust, wind
  direction, **wind-rose**, rain, rain rate/cumulative, UV, radiation, ET, cloudbase, apparent temp
- **Stats & climatology:** min/max/avg/sum tables; **climatological days** with configurable
  thresholds/labels; **climatogram** (calendar heatmap)
- **Data table** (all-data, paginated/sortable)
- **Archive pages** (day/month/year via SummaryBy*), **NOAA** reports
- **Celestial** (sun/moon/almanac), **Forecast** (Zambretti; optional external sources)
- **PWA** (manifest, service worker, offline), **MQTT live updates**, **light/dark** + user theming

## Proposed repo structure

```
bin/user/nordlys/            # clean-room SLE: data + config serialization (Python)
skins/Nordlys/
    skin.conf                # the config surface (documented)
    *.html.tmpl, includes/   # thin semantic shells + JSON payload + mount points
    dist/                    # built front-end (from Vite), shipped via copy_once
    lang/                    # i18n
src/                         # front-end: Svelte components/, charts/ (uPlot + SVG),
                             # theme/ (tokens), config-renderer, main.ts
vite.config.*, package.json, tsconfig.json
docs/                        # config reference, data-contract, theming guide, dev guide
install.py                   # weectl extension installer
tests/                       # Playwright E2E + Python unit
README.md, LICENSE
```

## Data contract (Python ↔ front-end)

Document a stable JSON shape, e.g.:
`{ meta, config: {…resolved skin.conf…}, current: {obs: {value, unit, …}}, series: {obs: [[t,v],…]},
stats: {…}, climatology: {…} }` - versioned, in `docs/data-contract.md`.

## Dev workflow & build

- Front-end: `vite dev` against JSON fixtures (fast iteration without weewx).
- Integration: `weectl report run` over a test DB; a small dev loop that rebuilds + regenerates.
- Ship: `vite build` → `dist/`; weewx `copy_once` deploys it. **Playwright** E2E against a generated
  site; Python unit tests for the SLE.

## Roadmap / milestones

1. **Scaffold** - repo structure, `install.py`, Vite + Svelte, minimal `skin.conf`, one page
   rendering current conditions from fixture JSON.
2. **Data layer** - SLE emitting `{config, data}`; wire a real weewx run end-to-end.
3. **Core dashboard** - implement the Nordlys design language as the `--nl-*` token set
   (polar-night + arctic-daylight); SVG gauges + stat tiles, config-driven.
4. **Charts + live** - integrate uPlot; full chart set; SVG wind-rose; MQTT live updates.
5. **Parity** - stats/climatology/tables/archive/NOAA/celestial/forecast.
6. **Config + docs** - harden the config model; write the config reference + theming guide.
7. **Polish** - PWA, a11y, performance budget, tests, `install.py` packaging, first release.

## Pitfalls to avoid

- **No shadow-DOM for themeable surfaces.** Keep the DOM open and CSS-token-driven; expose `::part`
  only if a web component is unavoidable. (In wdc, Carbon's header/tables were unreachable this way.)
- **Don't bake gauge/chart shapes into opaque compiled code** - keep them SVG + config/token driven.
- **Guard the minimal aesthetic.** New features must not add visual clutter; accent colors stay
  reserved for data/state/interaction; hairlines over boxes; if a tile needs a legend, rethink it.
- **weewx generates day/month/year summary pages once.** Any config/theme change must trigger a
  **regenerate-all** path (a helper or `stale_age`) or historical pages go stale - plan this in.
- **Keep chart palettes in CSS/config, not hardcoded.**
- **Ship the data contract** so Python and the front-end can evolve independently.

## References

- weewx 5 customization guide: Cheetah tags, **search-list extensions**, generators, unit system,
  `skin.conf` (`$current`, `$day/$week/$month/$year`, aggregates, `SummaryByDay/Month/Year`, `ToDate`).
- weewx-wdc (`Daveiano/weewx-wdc`) - study for feature scope and data needs; **do not copy** (clean-room).
