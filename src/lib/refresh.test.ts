// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { startAutoRefresh } from './refresh'

const T0 = 1_000_000_000_000 // ms
const GEN0 = T0 / 1000 // seconds
const INTERVAL = 300
const GRACE = 20_000
const RETRY = 60_000
// first fire: (GEN0 + INTERVAL)*1000 + GRACE - T0
const FIRST_DELAY = INTERVAL * 1000 + GRACE

function pageHtml(generatedAt: number, temp = 10): string {
  const payload = {
    meta: { generatedAt, updateInterval: INTERVAL },
    current: { outTemp: { value: temp, unit: '°C', label: 'T' } },
    config: {},
  }
  return `<!doctype html><html><body><script id="nordlys-data" type="application/json">${JSON.stringify(
    payload,
  )}</script></body></html>`
}

function okRes(body: string): Response {
  return { ok: true, text: async () => body } as unknown as Response
}

function setHidden(hidden: boolean) {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    get: () => hidden,
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  setHidden(false)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('startAutoRefresh', () => {
  it('schedules the first refresh at generatedAt + interval + grace', async () => {
    let lastUrl = ''
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      lastUrl = String(input)
      return okRes(pageHtml(GEN0 + INTERVAL))
    })
    const stop = startAutoRefresh({
      intervalSeconds: INTERVAL,
      getGeneratedAt: () => GEN0,
      onRefresh: () => {},
      fetchImpl,
      now: () => T0,
    })

    await vi.advanceTimersByTimeAsync(FIRST_DELAY - 1)
    expect(fetchImpl).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(fetchImpl).toHaveBeenCalledTimes(1)
    // fetch URL carries the cache-bust marker
    expect(lastUrl).toContain('_nl=')
    stop()
  })

  it('applies a newer payload and reschedules', async () => {
    let generatedAt = GEN0
    const onRefresh = vi.fn((p: { meta: { generatedAt: number } }) => {
      generatedAt = p.meta.generatedAt
    })
    const fetchImpl = vi.fn(async () => okRes(pageHtml(GEN0 + INTERVAL, 12)))
    const stop = startAutoRefresh({
      intervalSeconds: INTERVAL,
      getGeneratedAt: () => generatedAt,
      onRefresh,
      fetchImpl,
      now: () => T0,
    })

    await vi.advanceTimersByTimeAsync(FIRST_DELAY)
    expect(onRefresh).toHaveBeenCalledTimes(1)
    expect(onRefresh.mock.calls[0][0].meta.generatedAt).toBe(GEN0 + INTERVAL)
    stop()
  })

  it('does not apply an unchanged payload and retries sooner', async () => {
    const onRefresh = vi.fn()
    const fetchImpl = vi.fn(async () => okRes(pageHtml(GEN0))) // same generatedAt
    const stop = startAutoRefresh({
      intervalSeconds: INTERVAL,
      getGeneratedAt: () => GEN0,
      onRefresh,
      fetchImpl,
      now: () => T0,
    })

    await vi.advanceTimersByTimeAsync(FIRST_DELAY)
    expect(fetchImpl).toHaveBeenCalledTimes(1)
    expect(onRefresh).not.toHaveBeenCalled()
    // retry after RETRY_MS
    await vi.advanceTimersByTimeAsync(RETRY)
    expect(fetchImpl).toHaveBeenCalledTimes(2)
    stop()
  })

  it('backs off on a failed fetch', async () => {
    const onRefresh = vi.fn()
    const fetchImpl = vi.fn(async () => {
      throw new Error('offline')
    })
    const stop = startAutoRefresh({
      intervalSeconds: INTERVAL,
      getGeneratedAt: () => GEN0,
      onRefresh,
      fetchImpl,
      now: () => T0,
    })

    await vi.advanceTimersByTimeAsync(FIRST_DELAY)
    expect(fetchImpl).toHaveBeenCalledTimes(1)
    expect(onRefresh).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(RETRY)
    expect(fetchImpl).toHaveBeenCalledTimes(2)
    stop()
  })

  it('defers while hidden and catches up on visibilitychange', async () => {
    const onRefresh = vi.fn()
    const fetchImpl = vi.fn(async () => okRes(pageHtml(GEN0 + INTERVAL)))
    const stop = startAutoRefresh({
      intervalSeconds: INTERVAL,
      getGeneratedAt: () => GEN0,
      onRefresh,
      fetchImpl,
      now: () => T0,
    })

    setHidden(true)
    await vi.advanceTimersByTimeAsync(FIRST_DELAY)
    expect(fetchImpl).not.toHaveBeenCalled() // deferred while hidden

    setHidden(false)
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchImpl).toHaveBeenCalledTimes(1)
    expect(onRefresh).toHaveBeenCalledTimes(1)
    stop()
  })

  it('stops: clears the timer and removes the listener', async () => {
    const fetchImpl = vi.fn(async () => okRes(pageHtml(GEN0 + INTERVAL)))
    const stop = startAutoRefresh({
      intervalSeconds: INTERVAL,
      getGeneratedAt: () => GEN0,
      onRefresh: () => {},
      fetchImpl,
      now: () => T0,
    })

    stop()
    await vi.advanceTimersByTimeAsync(FIRST_DELAY * 3)
    expect(fetchImpl).not.toHaveBeenCalled()
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchImpl).not.toHaveBeenCalled()
  })
})
