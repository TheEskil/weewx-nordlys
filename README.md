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
```

## Installation

Not yet released. Once packaged: `weectl extension install <zip>`.
