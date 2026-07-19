import type { TileOptions } from './types'

/*
 * Config-driven tile coloring.
 *
 * options.color: a --nl-* token name ("accent-2") or a literal CSS color
 * ("#8be9fd") used for the tile's value/arc.
 * options.cold_below / hot_above: when the value crosses these bounds
 * (in report units), the semantic --nl-cold / --nl-hot tokens win.
 *
 * Returns a CSS color value, or undefined for "use the default".
 */
export function valueColor(
  value: number | null | undefined,
  options?: TileOptions,
): string | undefined {
  if (value !== null && value !== undefined) {
    if (options?.cold_below !== undefined && value < options.cold_below) {
      return 'var(--nl-cold)'
    }
    if (options?.hot_above !== undefined && value > options.hot_above) {
      return 'var(--nl-hot)'
    }
  }
  return cssColor(options?.color)
}

export function cssColor(color?: string): string | undefined {
  if (!color) return undefined
  return color.startsWith('#') || color.startsWith('rgb')
    ? color
    : `var(--nl-${color})`
}
