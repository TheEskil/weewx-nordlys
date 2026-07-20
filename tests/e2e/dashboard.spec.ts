import { expect, test } from '@playwright/test'

test.describe('dashboard (today fixture)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('renders station, gauges, and stat tiles', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: 'Aldersundet weather' }),
    ).toBeVisible()

    const tempGauge = page
      .locator('.tile', { hasText: 'Outside temperature' })
      .first()
    await expect(tempGauge.locator('.value')).toHaveText('13.6')

    // The stat tile (not the humidity chart) is the one with a .value.
    const humidity = page
      .locator('.tile', {
        hasText: 'Humidity',
        has: page.locator('.value'),
      })
      .first()
    await expect(humidity.locator('.value')).toContainText('79')
  })

  test('tile extremes carry their unit', async ({ page }) => {
    // A stat tile's min/avg/max must read "79 %", "13.6 °C" - not a bare
    // number that collides with the timestamp ("72 Sun 14:10").
    const humidity = page
      .locator('.tile', { hasText: 'Humidity', has: page.locator('.value') })
      .first()
    await expect(humidity.locator('.extremes')).toContainText('%')
  })

  test('renders the "on this day in history" tile', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: 'On this day in history' }),
    ).toBeVisible()
    // The records live in a tile of their own (section title is an h2).
    const history = page.locator('.tile', { hasText: 'Record high' }).first()
    await expect(history).toContainText('27.6°C')
    // Records are tagged with the year they occurred.
    await expect(history.getByText(/20\d{2}/).first()).toBeVisible()
  })

  test('shows the generated date in the footer and inline on the Now header', async ({
    page,
  }) => {
    // e.g. "Generated 19 Jul 2026, 16:55" - not "Jul 19, 2026, 4:55 PM".
    const footer = page.locator('footer')
    await expect(
      footer.getByText(/Generated \d{1,2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2}/),
    ).toBeVisible()
    await expect(footer).not.toContainText(/\bPM\b|\bAM\b/)
    // Echoed inline on the first section's title: "Now · 19 Jul 2026, 16:55".
    await expect(page.locator('.h2-date')).toContainText(
      /\d{1,2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2}/,
    )
  })

  test('renders charts, wind rose, almanac, and forecast', async ({
    page,
  }) => {
    // uPlot draws into canvases.
    await expect(page.locator('.chart canvas').first()).toBeVisible()
    await expect(
      page.locator('.tile', { hasText: 'Wind rose' }).locator('path').first(),
    ).toBeVisible()
    await expect(page.getByText('Day length 20:16')).toBeVisible()
    await expect(page.getByText('Fine weather')).toBeVisible()
    await expect(page.getByText('Zambretti B')).toBeVisible()
  })

  test('records table sorts and paginates', async ({ page }) => {
    const table = page.locator('.tile', { hasText: 'Time' }).last()
    await expect(table.getByText('1 / 12')).toBeVisible()

    const firstValue = await table
      .locator('tbody tr')
      .first()
      .locator('td')
      .nth(1)
      .textContent()

    // Sort by outside temperature descending: first row is the max.
    await table
      .getByRole('button', { name: /Outside temperature/ })
      .click()
    const sortedValue = await table
      .locator('tbody tr')
      .first()
      .locator('td')
      .nth(1)
      .textContent()
    expect(Number(sortedValue)).toBeGreaterThanOrEqual(Number(firstValue))

    await table.getByRole('button', { name: 'Older ›' }).click()
    await expect(table.getByText('2 / 12')).toBeVisible()
  })

  test('stats table shows aggregates', async ({ page }) => {
    const stats = page.locator('.tile', { hasText: 'Avg' }).last()
    await expect(stats.getByText('Tue 04:20')).toBeVisible()
    await expect(stats.getByRole('columnheader', { name: 'Total' })).toBeVisible()
  })
})

test.describe('semantic coloring (extremes fixture)', () => {
  test('cold and hot thresholds color values', async ({ page }) => {
    await page.goto('/?fixture=extremes')

    // Feels like -16.3 °C with cold_below: 0 -> ice teal (--nl-cold).
    const feelsLike = page
      .locator('.tile', { hasText: 'Feels like' })
      .first()
      .locator('.value')
    await expect(feelsLike).toHaveCSS('color', 'rgb(76, 201, 240)')

    // Wind gust 26.1 with hot_above: 20 -> hot orange (--nl-hot).
    const gust = page
      .locator('.tile', { hasText: 'Wind gust' })
      .first()
      .locator('.value')
    await expect(gust).toHaveCSS('color', 'rgb(240, 138, 92)')
  })

  test('light mode swaps the palette', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' })
    await page.goto('/?fixture=extremes')
    const feelsLike = page
      .locator('.tile', { hasText: 'Feels like' })
      .first()
      .locator('.value')
    // Light-mode --nl-cold.
    await expect(feelsLike).toHaveCSS('color', 'rgb(14, 116, 144)')
  })
})
