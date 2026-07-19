import type { NordlysPayload, TileConfig } from './types'

/** Observation keys the SLE flagged as having no data (absent sensors). */
export function emptyObsSet(payload: NordlysPayload): Set<string> {
  return new Set(payload.emptyObs ?? [])
}

export function obsKeysOf(tile: TileConfig): string[] {
  return Array.isArray(tile.obs) ? tile.obs : tile.obs ? [tile.obs] : []
}

/**
 * A tile is hidden when every observation it references is empty, unless
 * it opts out with `always_show`. Tiles with no observation (forecast,
 * celestial, climatology, text) are never hidden here.
 */
export function tileIsEmpty(tile: TileConfig, payload: NordlysPayload): boolean {
  if (tile.options?.always_show) return false
  const keys = obsKeysOf(tile)
  if (keys.length === 0) return false
  const empty = emptyObsSet(payload)
  return keys.every((key) => empty.has(key))
}
