import './theme/tokens.css'
import './theme/base.css'
import { mount } from 'svelte'
import App from './App.svelte'
import { applyTheme } from './lib/theme'
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
  const src = el.getAttribute('data-src')
  if (src) {
    const res = await fetch(src)
    if (!res.ok) throw new Error(`Nordlys: loading ${src} failed (${res.status})`)
    return (await res.json()) as NordlysPayload
  }
  return JSON.parse(el.textContent ?? '') as NordlysPayload
}

const target = document.getElementById('nordlys-app')
if (!target) throw new Error('Nordlys: missing #nordlys-app mount point')

loadPayload().then((payload) => {
  applyTheme(payload.config.theme)
  mount(App, { target, props: { payload } })
})
