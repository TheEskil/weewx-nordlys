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
  /** span ('day' | 'week' | …) -> obs -> series */
  series?: Record<string, Record<string, SeriesEntry>>
  /** span -> wind-rose distribution */
  windrose?: Record<string, WindRoseData>
}

export interface SeriesEntry {
  unit: string
  label: string
  decimals: number
  /** [unix seconds, value|null] pairs, oldest first */
  points: [number, number | null][]
  /** aggregation applied by the SLE ('avg' | 'sum'), absent for raw */
  aggregate?: string
}

export interface WindRoseData {
  unit: string
  /** speed band upper bounds (report units); the last band is open-ended */
  bands: number[]
  /** percent of samples that were calm (or had no direction) */
  calm: number
  samples: number
  /** 16 sectors (N first, clockwise) x bands+1 percentages */
  sectors: number[][]
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
  live?: LiveConfig
}

export interface LiveConfig {
  /** MQTT broker WebSocket URL, e.g. wss://host:9001 */
  broker: string
  /** topic with JSON loop payloads; keys are weewx obs names
   * (unit suffixes like outTemp_C are stripped) */
  topic?: string
  [key: string]: unknown
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
  /** chart tiles may plot several observations */
  obs?: string | string[]
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
  /** chart kind: line | area | bar | scatter | windrose */
  chart?: string
  /** chart timespan: day | week | month | year (default day) */
  span?: string
  /** wind-rose speed band upper bounds (report units) */
  bands?: number[]
  /** wind-rose calm threshold (report units) */
  calm_below?: number
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
