import { expect, test } from '@playwright/test'
import { Aedes } from 'aedes'
import { WebSocketServer, createWebSocketStream } from 'ws'

const PORT = 9013

let aedes: InstanceType<typeof Aedes>
let wss: WebSocketServer
let timer: ReturnType<typeof setInterval>

test.beforeAll(async () => {
  aedes = await Aedes.createBroker()
  wss = new WebSocketServer({ port: PORT })
  wss.on('connection', (ws) => {
    aedes.handle(createWebSocketStream(ws) as never)
  })
  let temp = 20
  timer = setInterval(() => {
    temp += 0.7
    aedes.publish(
      {
        cmd: 'publish',
        qos: 0,
        dup: false,
        retain: false,
        topic: 'weather/loop',
        payload: JSON.stringify({ outTemp_C: +temp.toFixed(1) }),
      },
      () => {},
    )
  }, 500)
})

test.afterAll(async () => {
  clearInterval(timer)
  wss.close()
  aedes.close()
})

test('live MQTT updates flow into tiles', async ({ page }) => {
  await page.goto(`/?live=ws://localhost:${PORT}`)

  const indicator = page.locator('.live.connected')
  await expect(indicator).toBeVisible({ timeout: 10000 })

  const gauge = page
    .locator('.tile', { hasText: 'Outside temperature' })
    .first()
    .locator('.value')

  // Fixture value is 13.6; the broker publishes rising values >= 20.
  await expect
    .poll(async () => Number(await gauge.textContent()), { timeout: 10000 })
    .toBeGreaterThan(19)
})
