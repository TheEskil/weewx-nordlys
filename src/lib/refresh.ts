import type { NordlysPayload } from './types'
import { parseEmbeddedPayload } from './payload'

export interface AutoRefreshOptions {
  /** report cadence in seconds (payload meta.updateInterval) */
  intervalSeconds: number
  /** latest known report time (unix seconds); read fresh on every tick */
  getGeneratedAt: () => number
  /** called with a newer payload when the report has regenerated */
  onRefresh: (fresh: NordlysPayload) => void
  /** injectable for tests; defaults to the global fetch */
  fetchImpl?: typeof fetch
  /** injectable clock (ms); defaults to Date.now */
  now?: () => number
}

// Reports are written a few seconds after the interval boundary; the grace
// delay avoids a wasted early fetch and absorbs small server->client clock
// skew. The floor keeps a stale/past generatedAt (or a fast client clock)
// from scheduling a near-zero delay and hot-looping. The retry is used when
// the report has not regenerated yet or a fetch/parse failed.
const GRACE_MS = 20_000
const MIN_MS = 30_000
const RETRY_MS = 60_000

/**
 * Periodically re-fetches this page's own HTML (cache-bypassed) and hands a
 * newer payload to `onRefresh`, timed to the report cadence. Pauses while the
 * tab is hidden and catches up when it becomes visible again. Returns a stop
 * function (mirrors startLive).
 */
export function startAutoRefresh(opts: AutoRefreshOptions): () => void {
  const doFetch = opts.fetchImpl ?? fetch
  const now = opts.now ?? Date.now

  let timer: ReturnType<typeof setTimeout> | undefined
  let pending = false
  let stopped = false

  function scheduleIn(delayMs: number) {
    clearTimeout(timer)
    timer = setTimeout(fire, Math.max(delayMs, 0))
  }

  function scheduleNext(fromGeneratedAt: number) {
    const targetMs = (fromGeneratedAt + opts.intervalSeconds) * 1000 + GRACE_MS
    scheduleIn(Math.max(targetMs - now(), MIN_MS))
  }

  function fire() {
    if (stopped) return
    if (typeof document !== 'undefined' && document.hidden) {
      pending = true // caught up by the visibility handler
      return
    }
    void doRefresh()
  }

  async function doRefresh() {
    pending = false
    try {
      const url = new URL(location.href)
      url.searchParams.set('_nl', String(now())) // cache-bust + sw.js bypass
      const res = await doFetch(url, { cache: 'no-store' })
      if (!res.ok) return scheduleIn(RETRY_MS)
      const html = await res.text()
      const doc = new DOMParser().parseFromString(html, 'text/html')
      const fresh = parseEmbeddedPayload(doc)
      if (stopped) return
      if (fresh.meta.generatedAt > getGeneratedAtSafe()) {
        opts.onRefresh(fresh)
        scheduleNext(fresh.meta.generatedAt)
      } else {
        // Report throttled (report_timing / stale_age) or not yet
        // regenerated; poll again sooner than a full interval.
        scheduleIn(RETRY_MS)
      }
    } catch {
      if (!stopped) scheduleIn(RETRY_MS)
    }
  }

  function getGeneratedAtSafe() {
    return opts.getGeneratedAt()
  }

  function onVisible() {
    if (stopped || (typeof document !== 'undefined' && document.hidden)) return
    const dueAt = (getGeneratedAtSafe() + opts.intervalSeconds) * 1000 + GRACE_MS
    if (pending || dueAt <= now()) {
      pending = false
      clearTimeout(timer)
      void doRefresh()
    }
  }

  document.addEventListener('visibilitychange', onVisible)
  scheduleNext(getGeneratedAtSafe())

  return () => {
    stopped = true
    clearTimeout(timer)
    document.removeEventListener('visibilitychange', onVisible)
  }
}
