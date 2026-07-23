import type { NordlysPayload } from './types'

/**
 * Parse the `#nordlys-data` <script> JSON out of a document or fragment.
 * Shared by the initial boot (main.ts) and the auto-refresh module, which
 * parses a freshly-fetched copy of the page.
 */
export function parseEmbeddedPayload(root: ParentNode): NordlysPayload {
  const el = root.querySelector('#nordlys-data')
  if (!el?.textContent)
    throw new Error('Nordlys: missing #nordlys-data payload element')
  return JSON.parse(el.textContent) as NordlysPayload
}
