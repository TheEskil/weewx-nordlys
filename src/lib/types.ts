/*
 * The Python <-> front-end data contract, version 1.
 * Mirrors what the Nordlys search-list extension serializes; the dev
 * fixtures in fixtures/ follow the same shape. Documented in
 * docs/data-contract.md (kept in sync with these types).
 */

export interface NordlysPayload {
  meta: Meta
  config: SkinConfig
  current: Record<string, Observation>
}

export interface Meta {
  version: number
  generatedAt: number
  station: Station
}

export interface Station {
  name: string
  location: string
  latitude: number
  longitude: number
  altitude?: string
}

export interface SkinConfig {
  theme?: ThemeConfig
  pages: PageConfig[]
}

export interface ThemeConfig {
  mode?: 'auto' | 'dark' | 'light'
  /** --nl-* token overrides, without the prefix (e.g. accent = "#3ddc97") */
  dark?: Record<string, string>
  light?: Record<string, string>
}

export interface PageConfig {
  id: string
  title: string
  layout: RowConfig[]
}

export interface RowConfig {
  title?: string
  /** Max columns on wide screens; the grid collapses responsively. */
  columns?: number
  tiles: TileConfig[]
}

export type TileType = 'gauge' | 'stat' | 'chart' | 'table' | 'text'

export interface TileConfig {
  type: TileType
  obs?: string
  title?: string
  options?: TileOptions
}

export interface TileOptions {
  min?: number
  max?: number
  /** gauge style; 'compass' renders a wind-direction compass */
  style?: string
  /** --nl-* token name (without prefix) or literal CSS color for the value/arc */
  color?: string
  /** below this value (report units), the --nl-cold semantic token applies */
  cold_below?: number
  /** above this value (report units), the --nl-hot semantic token applies */
  hot_above?: number
  [key: string]: unknown
}

export interface Observation {
  value: number | null
  unit: string
  label: string
  decimals?: number
  min?: Extreme
  max?: Extreme
  /** change over the trend window, in the observation's unit */
  trend?: number | null
}

export interface Extreme {
  value: number | null
  time?: string
}
