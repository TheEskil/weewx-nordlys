#!/usr/bin/env node
/*
 * Local MQTT-over-WebSocket broker that publishes synthetic weewx loop
 * packets - for developing/testing Nordlys live updates without a real
 * broker.
 *
 * Usage: node dev/live-sim.mjs [port]   (default 9002)
 * Then open the dev harness with ?live=ws://localhost:9002
 */

import { Aedes } from 'aedes'
import { WebSocketServer, createWebSocketStream } from 'ws'

const port = Number(process.argv[2] ?? 9002)
const aedes = await Aedes.createBroker()

const wss = new WebSocketServer({ port })
wss.on('connection', (ws) => {
  aedes.handle(createWebSocketStream(ws))
})

let tick = 0
setInterval(() => {
  tick += 1
  const packet = {
    // Unit-suffixed keys, like the weewx MQTT uploader publishes.
    outTemp_C: +(14 + 2 * Math.sin(tick / 5) + Math.random()).toFixed(1),
    outHumidity: Math.round(75 + 8 * Math.sin(tick / 7)),
    barometer_mbar: +(1012 + Math.sin(tick / 30)).toFixed(1),
    windSpeed_mps: +(4 + 2.5 * Math.abs(Math.sin(tick / 3))).toFixed(1),
    windGust_mps: +(6 + 3 * Math.abs(Math.sin(tick / 3))).toFixed(1),
    windDir: Math.round((210 + 40 * Math.sin(tick / 6) + 360) % 360),
    dayRain_mm: +(1.2 + tick * 0.01).toFixed(2),
  }
  aedes.publish(
    { topic: 'weather/loop', payload: JSON.stringify(packet) },
    () => {},
  )
}, 2000)

console.log(`MQTT-over-WebSocket broker on ws://localhost:${port}`)
console.log('publishing synthetic loop packets to "weather/loop" every 2s')
