# weewx-nordlys

*Nordlys* ("northern lights") is a clean, minimal, config-first skin for
[weewx](https://weewx.com). The entire dashboard - pages, layout, tiles,
charts, theme - is configured from `skin.conf`; no template or JavaScript
edits are ever needed.

**Status: early development.** See [PLAN.md](PLAN.md) for the design and
roadmap.

## Design

- Dark-first "polar night" theme with aurora accents; derived "arctic
  daylight" light mode; follows the visitor's system preference
- All styling via `--nl-*` CSS design tokens, overridable from
  `skin.conf` `[[theme]]` or a `user.css`
- Svelte + Vite front-end, uPlot + hand-rolled SVG for charts and gauges
- Server-rendered fallback values; JS enhances progressively

## Development

```sh
npm install
npm run dev     # dev server against fixtures/ JSON (no weewx needed)
npm run build   # builds the front-end into skins/Nordlys/dist/
npm run check   # svelte-check / TypeScript
npm test        # vitest unit tests
```

The dev server renders `fixtures/today.json`; append `?fixture=extremes`
to preview the winter-storm fixture (semantic cold/hot coloring).

To develop live updates without a real MQTT broker:

```sh
node dev/live-sim.mjs        # broker on ws://localhost:9002, synthetic loop packets
# then open http://localhost:5173/?live=ws://localhost:9002
```

To exercise the full weewx pipeline locally (report generation with a
synthetic 7-day archive database):

```sh
python3 -m venv .venv && .venv/bin/pip install weewx
.venv/bin/python dev/setup.py      # one-time station area in dev/weewx/
npm run build                       # SLE serves the built assets
.venv/bin/weectl report run --config dev/weewx/weewx.conf
python3 -m http.server 8123 --directory dev/weewx/public_html/nordlys

.venv/bin/python -m unittest discover tests/python   # SLE unit tests
```

The Python <-> front-end payload shape is documented in
[docs/data-contract.md](docs/data-contract.md).

## Installation

Not yet released. Once packaged: `weectl extension install <zip>`.
