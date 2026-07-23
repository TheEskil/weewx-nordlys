/*
 * Nordlys service worker.
 *
 * - Pages (navigations): network first, cached fallback - the payload
 *   is embedded in the HTML, so fresh data wins and offline still shows
 *   the last generated report.
 * - Assets: stale-while-revalidate - asset filenames are stable, so
 *   serve fast and refresh in the background.
 */

const CACHE = 'nordlys-v1'
const PRECACHE = ['./', 'dist/nordlys.js', 'dist/nordlys.css', 'icon.svg']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== location.origin) return

  // Auto-refresh re-fetch (?_nl=<ts>): go straight to the network and never
  // cache it, so the open page always gets the freshly generated payload.
  if (url.searchParams.has('_nl')) {
    event.respondWith(fetch(request))
    return
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE).then((cache) => cache.put(request, copy))
          return response
        })
        .catch(() => caches.match(request).then((hit) => hit ?? caches.match('./'))),
    )
    return
  }

  event.respondWith(
    caches.match(request).then((hit) => {
      const refresh = fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone()
            caches.open(CACHE).then((cache) => cache.put(request, copy))
          }
          return response
        })
        .catch(() => hit)
      return hit ?? refresh
    }),
  )
})
