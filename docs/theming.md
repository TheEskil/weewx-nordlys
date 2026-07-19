# Nordlys theming guide

Nordlys is themed entirely through CSS design tokens (`--nl-*` custom
properties). The dark **polar night** palette is the hero theme; the
light **arctic daylight** palette is derived from it. By default the
site follows the visitor's system preference.

Every surface, text, accent, chart series, and semantic color is a
token. There is no shadow DOM and no compiled-in styling - anything you
can see, you can re-theme from config.

## Choosing the mode

```ini
[Nordlys]
    [[theme]]
        mode = auto     # auto (default) | dark | light
```

## Overriding tokens

Token names are the custom properties without the `--nl-` prefix,
overridden per mode:

```ini
    [[theme]]
        [[[dark]]]
            accent = "#e86bc1"      # magenta aurora instead of green
            bg = "#0a0a14"
        [[[light]]]
            accent = "#7c3aed"
```

Dark overrides apply whenever dark mode is active (forced or via system
preference), light overrides likewise. Quote hex colors so the `#` is
not read as a comment.

## Token reference

Defaults below; dark first, light second.

### Surfaces & text

| token | dark | light | role |
|---|---|---|---|
| `bg` | `#0b1220` | `#f6f9fc` | page background |
| `surface` | `#111a2c` | `#ffffff` | tiles/cards |
| `border` | `#1e2a40` | `#d7e0eb` | 1px hairlines |
| `text` | `#e8eef7` | `#17263b` | primary text |
| `text-dim` | `#8fa3bf` | `#5b6c82` | labels, units, secondary text |

### Aurora accents

| token | dark | light | role |
|---|---|---|---|
| `accent` | `#3ddc97` | `#0e9f6e` | primary accent (gauge arcs, links, active nav) |
| `accent-2` | `#4cc9f0` | `#0e7490` | ice teal |
| `accent-3` | `#a78bfa` | `#7c3aed` | aurora violet |
| `accent-4` | `#e86bc1` | `#c2338f` | magenta (use sparingly) |
| `warm` | `#f0b860` | `#b07817` | muted amber |

### Data semantics

| token | dark | light | role |
|---|---|---|---|
| `cold` / `hot` | `#4cc9f0` / `#f08a5c` | `#0e7490` / `#c2410c` | threshold coloring, calendar ramp |
| `ok` / `alert` | `#3ddc97` / `#f27e7e` | `#0e9f6e` / `#c0362c` | status (live indicator, alerts) |
| `series-1` … `series-6` | aurora palette | darkened | chart series order |

### Space, shape, type

| token | default | role |
|---|---|---|
| `space-0` … `space-8` | 4-64 px | spacing scale (8px grid) |
| `radius` | `8px` | tile corner radius |
| `max-width` | `1200px` | content width |
| `font` | system UI stack | the one typeface |
| `fs-sm` / `fs-base` / `fs-lg` / `fs-xl` | 13/15/20/32 px | type scale |

The full authoritative list is `src/theme/tokens.css`.

## Guidance

- **Keep surfaces monochrome.** The design language reserves color for
  data, state, and interaction. If everything is colored, nothing is.
- **Contrast:** body text tokens are chosen for >= 4.5:1 against their
  backgrounds; accents for >= 3:1 as non-text elements. If you override
  `accent` in light mode, darken it - the dark-mode value will usually
  fail contrast on white.
- Where tiles color values (`cold_below`, `hot_above`,
  `color = <token>`), prefer the semantic and accent tokens over raw hex
  so your palette stays consistent and re-themeable.

## Beyond tokens: user.css

For changes tokens cannot express (layout tweaks, hiding elements),
ship an extra stylesheet:

```ini
[Nordlys]
    user_css = user.css
```

Put `user.css` next to the generated site (e.g. copy it via a
`[CopyGenerator]` `copy_once` entry, or drop it in `HTML_ROOT`). It
loads after `nordlys.css`, so its rules win.

## Per-station overrides

Everything above also works from weewx.conf without touching the skin:

```ini
[StdReport]
    [[NordlysReport]]
        [[[Nordlys]]]
            [[[[theme]]]]
                mode = dark
                [[[[[dark]]]]]
                    accent = "#4cc9f0"
```
