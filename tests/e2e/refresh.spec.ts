import { expect, test } from '@playwright/test'
import { readFileSync } from 'fs'

// The dev harness serves fixtures/today.json via data-src; the production
// re-fetch path (embedded #nordlys-data) is exercised here with ?refresh=1
// (force-enables auto-refresh in dev) plus route interception.
const base = JSON.parse(readFileSync('fixtures/today.json', 'utf8'))

function embed(payload: unknown): string {
  const json = JSON.stringify(payload).replace(/</g, '\\u003c')
  return `<!doctype html><html><body><script id="nordlys-data" type="application/json">${json}</script></body></html>`
}

test('auto-refresh swaps fresh data into the page in place', async ({
  page,
}) => {
  // Initial payload: an old generatedAt so the visibility path is "overdue"
  // and refreshes immediately instead of waiting out the real timer.
  const initial = structuredClone(base)
  initial.meta.generatedAt = 1_000_000_000
  initial.meta.updateInterval = 60
  await page.route('**/fixtures/today.json', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(initial),
    }),
  )

  // The re-fetch (…?_nl=…) returns a newer report with a changed temperature.
  const fresh = structuredClone(base)
  fresh.meta.generatedAt = 1_000_100_000
  fresh.current.outTemp.value = 99.9
  await page.route('**/*_nl=*', (route) =>
    route.fulfill({ contentType: 'text/html', body: embed(fresh) }),
  )

  await page.goto('/?refresh=1')

  const gauge = page
    .locator('.tile', { hasText: 'Outside temperature' })
    .first()
    .locator('.value')
  await expect(gauge).toBeVisible()

  // Nudge the visibility handler: generatedAt is far in the past, so it is
  // overdue and refreshes at once.
  await page.evaluate(() =>
    document.dispatchEvent(new Event('visibilitychange')),
  )

  await expect
    .poll(async () => Number(await gauge.textContent()), { timeout: 10000 })
    .toBeGreaterThan(99)
})
