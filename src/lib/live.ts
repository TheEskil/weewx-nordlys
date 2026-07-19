import type { LiveConfig } from './types'

export type LiveStatus = 'off' | 'connecting' | 'connected' | 'error'

const DEFAULT_TOPIC = 'weather/loop'

/**
 * Connects to the configured MQTT broker (over WebSocket) and reports
 * numeric observation updates. Payloads are JSON objects whose keys are
 * weewx observation names, optionally with a unit suffix (outTemp_C),
 * which is stripped. dayRain maps onto the rain (day total) tile.
 *
 * The mqtt client library is loaded on demand, so stations without
 * [live] config never download it.
 *
 * Returns a stop function.
 */
export function startLive(
  config: LiveConfig,
  onData: (updates: Record<string, number>) => void,
  onStatus: (status: LiveStatus) => void,
): () => void {
  let stopped = false
  let client: { end: (force: boolean) => void } | undefined

  onStatus('connecting')
  import('mqtt')
    .then((mqtt) => {
      if (stopped) return
      const connection = mqtt.default.connect(config.broker, {
        reconnectPeriod: 5000,
        connectTimeout: 10000,
      })
      client = connection

      connection.on('connect', () => {
        onStatus('connected')
        connection.subscribe(config.topic ?? DEFAULT_TOPIC)
      })
      connection.on('close', () => {
        if (!stopped) onStatus('connecting')
      })
      connection.on('error', () => onStatus('error'))
      connection.on('message', (_topic: string, buffer: Uint8Array) => {
        const updates = parseLoopPayload(new TextDecoder().decode(buffer))
        if (updates) onData(updates)
      })
    })
    .catch(() => onStatus('error'))

  return () => {
    stopped = true
    onStatus('off')
    client?.end(true)
  }
}

export function parseLoopPayload(
  text: string,
): Record<string, number> | null {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return null
  }
  if (typeof raw !== 'object' || raw === null) return null

  const updates: Record<string, number> = {}
  for (const [key, value] of Object.entries(raw)) {
    const num = typeof value === 'string' ? Number(value) : value
    if (typeof num !== 'number' || !Number.isFinite(num)) continue
    const base = key.replace(/_[A-Za-z0-9%²/]+$/, '')
    updates[base] = num
  }
  if ('dayRain' in updates) {
    updates.rain = updates.dayRain
  }
  return Object.keys(updates).length > 0 ? updates : null
}
