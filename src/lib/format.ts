import type { Observation } from './types'

export function formatValue(
  value: number | null | undefined,
  decimals = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return value.toFixed(decimals)
}

export function formatObs(obs: Observation): string {
  return formatValue(obs.value, obs.decimals ?? 1)
}

const COMPASS_POINTS = [
  'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
]

export function degToCompass(deg: number | null | undefined): string {
  if (deg === null || deg === undefined || Number.isNaN(deg)) return '-'
  const index = Math.round((((deg % 360) + 360) % 360) / 22.5) % 16
  return COMPASS_POINTS[index]
}

export function formatTrend(trend: number, decimals = 1): string {
  const arrow = trend > 0 ? '↗' : trend < 0 ? '↘' : '→'
  return `${arrow} ${formatValue(Math.abs(trend), decimals)}`
}
