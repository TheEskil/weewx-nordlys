import type { Observation, StatsEntry } from './types'

/**
 * Adapt a period StatsEntry into the Observation shape a stat tile
 * renders. The hero value is the period average (the total for sum
 * observations like rain); the detail row keeps only the extremes, since
 * the average is now the hero. No trend - that is a current-conditions
 * concept.
 */
export function periodObs(entry: StatsEntry): Observation {
  const isSum = entry.sum !== undefined
  return {
    value: isSum ? (entry.sum ?? null) : (entry.avg ?? null),
    unit: entry.unit,
    label: entry.label,
    decimals: entry.decimals,
    min: isSum ? undefined : entry.min,
    max: entry.max,
  }
}
