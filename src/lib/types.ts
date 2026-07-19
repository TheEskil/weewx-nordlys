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
  /** obs with no data over the archive (absent sensors); their tiles
   * and stats rows are hidden unless a tile sets always_show */
  emptyObs?: string[]
  /** span ('day' | 'week' | …) -> obs -> series */
  series?: Record<string, Record<string, SeriesEntry>>
  /** span -> wind-rose distribution */
  windrose?: Record<string, WindRoseData>
  /** span ('week' | 'month' | 'year' | 'alltime') -> obs -> aggregates */
  stats?: Record<string, Record<string, StatsEntry>>
  climatology?: Climatology | null
  almanac?: AlmanacData | null
  forecast?: ForecastData | null
  /** set on archive (SummaryBy month/year) pages */
  period?: PeriodInfo | null
  /** all months/years in the database, for reports tiles */
  archives?: ArchivesIndex | null
}

export interface PeriodInfo {
  kind: 'week' | 'month' | 'year'
  /** matches the archives-index id for the picker's current selection */
  id: string
  label: string
}

export interface ArchivesIndex {
  weeks: ArchiveLink[]
  months: ArchiveLink[]
  years: ArchiveLink[]
}

export interface ArchiveLink {
  id: string
  label: string
  /** short month name; months only */
  month?: string
  /** owning year; months only */
  year?: string
  /** archive page filename */
  page: string
  /** NOAA text report path; months/years only */
  noaa?: string
}

export interface StatsEntry {
  label: string
  unit: string
  decimals: number
  min?: Extreme
  max?: Extreme
  avg?: number
  /** present for sum observations (rain); max is then the wettest day */
  sum?: number
}

export interface Climatology {
  days?: ClimoDay[]
  calendar?: CalendarData
  /** every year in the archive (newest first) for the Climate year picker */
  years?: ClimateYear[]
}

export interface ClimateYear {
  year: string
  /** partial-year coverage, e.g. "2026 (so far)", "2025 (from Apr)" */
  label: string
}

/** climate-<year>.json: the year-scoped slice swapped in by the picker */
export interface ClimateSlice {
  year: string
  climatology: { days?: ClimoDay[]; calendar?: CalendarData }
  stats: Record<string, Record<string, StatsEntry>>
}

export interface ClimoDay {
  id: string
  label: string
  count: number
  obs: string
  aggregate: string
  op: string
  value: number
  unit: string
}

export interface CalendarData {
  obs: string
  label: string
  aggregate: string
  unit: string
  /** [day-start unix seconds, value|null], oldest first */
  days: [number, number | null][]
}

export interface AlmanacData {
  sunrise: string | null
  sunset: string | null
  day_length?: string
  /** polar latitudes: the sun never sets / never rises today */
  always_up?: boolean
  always_down?: boolean
  moon_phase: string
  moon_fullness: number
  /** pyephem present: the Celestial-page sections below are populated */
  hasExtras?: boolean
  // --- extras (require ephem) ---
  transit?: string | null
  sun_alt?: number
  sun_az?: number
  /** minutes from local midnight at report time (sun-path marker) */
  sun_now?: number
  /** change in day length vs yesterday, seconds (negative = shorter) */
  day_length_delta?: number
  twilight?: {
    civil?: [string | null, string | null]
    nautical?: [string | null, string | null]
    astronomical?: [string | null, string | null]
  }
  /** [minutes-from-midnight, solar altitude °] every 30 min */
  sun_path?: [number, number][]
  moonrise?: string | null
  moonset?: string | null
  next_full_moon?: string | null
  next_new_moon?: string | null
  seasons?: {
    equinox?: { date: string; days: number }
    solstice?: { date: string; days: number; kind: 'summer' | 'winter' }
  }
  planets?: { name: string; rise: string | null; set: string | null }[]
}

export interface ForecastData {
  code: string
  text: string
  trend: 'rising' | 'steady' | 'falling'
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
  /** a period picker jumps to per-week/month/year archive pages */
  picker?: 'week' | 'month' | 'year'
}

export interface RowConfig {
  title?: string
  /** Max columns on wide screens; the grid collapses responsively. */
  columns?: number
  tiles: TileConfig[]
}

export type TileType =
  | 'gauge'
  | 'stat'
  | 'chart'
  | 'table'
  | 'text'
  | 'climatology'
  | 'celestial'
  | 'forecast'
  | 'reports'

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
  /** chart timespan: 24h | day | yesterday | week | month | year
   * (default day = calendar today; 24h = trailing window).
   * On a stat tile, a span (yesterday/week/month/year/alltime/archive)
   * makes it a period stat rendered from stats[span] instead of current. */
  span?: string
  /** wind-rose speed band upper bounds (report units) */
  bands?: number[]
  /** wind-rose calm threshold (report units) */
  calm_below?: number
  /** table kind: stats (default) | records */
  table?: string
  /** calendar chart daily aggregate: avg (default) | min | max | sum */
  aggregate?: string
  /** keep this tile visible even when its observation has no data */
  always_show?: boolean
  [key: string]: unknown
}

export interface Observation {
  value: number | null
  unit: string
  label: string
  decimals?: number
  min?: Extreme
  max?: Extreme
  /** period average (report-time; not extended by live updates) */
  avg?: number
  /** change over the trend window, in the observation's unit */
  trend?: number | null
}

export interface Extreme {
  value: number | null
  time?: string
}
