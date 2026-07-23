import './theme/tokens.css'
import './theme/base.css'
import { mount } from 'svelte'
import App from './App.svelte'
import { applyTheme } from './lib/theme'
import { parseEmbeddedPayload } from './lib/payload'
import type { NordlysPayload } from './lib/types'

/*
 * The page shell (Cheetah template, or index.html in dev) provides:
 *   <script id="nordlys-data" type="application/json">…payload…</script>
 *   <div id="nordlys-app"></div>
 * In dev the payload element carries data-src pointing at a JSON fixture.
 */
async function loadPayload(): Promise<NordlysPayload> {
  const el = document.getElementById('nordlys-data')
  if (!el) throw new Error('Nordlys: missing #nordlys-data payload element')
  let src = el.getAttribute('data-src')
  if (src) {
    // Dev harness only (data-src is never set in production): allow
    // ?fixture=<name> to load an alternative fixture, and
    // ?live=ws://host:port to exercise live updates (see dev/live-sim.mjs).
    const params = new URLSearchParams(location.search)
    const fixture = params.get('fixture')
    if (fixture && /^[\w-]+$/.test(fixture)) src = `/fixtures/${fixture}.json`
    const res = await fetch(src)
    if (!res.ok) throw new Error(`Nordlys: loading ${src} failed (${res.status})`)
    const payload = (await res.json()) as NordlysPayload
    const live = params.get('live')
    if (live) payload.config.live = { broker: live }
    return payload
  }
  return parseEmbeddedPayload(document)
}

const target = document.getElementById('nordlys-app')
if (!target) throw new Error('Nordlys: missing #nordlys-app mount point')

// The dev harness marks itself with data-src on the payload element; in
// production the payload is embedded. Auto-refresh and the PWA service
// worker are production-only.
const isDev = !!document
  .getElementById('nordlys-data')
  ?.hasAttribute('data-src')

loadPayload().then((payload) => {
  applyTheme(payload.config.theme)
  target.replaceChildren() // drop the server-rendered fallback
  mount(App, { target, props: { payload, dev: isDev } })
})

if (!isDev && 'serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js').catch(() => {
    /* offline support is best-effort */
  })
}
