#!/usr/bin/env node
/*
 * Performance budget: fails when the shipped bundles outgrow the
 * "lean & fast" principle. Run after `npm run build`.
 */
import { readFileSync } from 'fs'
import { gzipSync } from 'zlib'

const BUDGETS_KB = {
  'skins/Nordlys/dist/nordlys.js': 60, // core bundle incl. uPlot
  'skins/Nordlys/dist/nordlys.css': 8,
  'skins/Nordlys/dist/nordlys.mqtt.esm.js': 130, // lazy, live-only chunk
}

let failed = false
for (const [file, budget] of Object.entries(BUDGETS_KB)) {
  const gzipped = gzipSync(readFileSync(file)).length / 1024
  const ok = gzipped <= budget
  console.log(
    `${ok ? 'ok  ' : 'FAIL'} ${file}: ${gzipped.toFixed(1)} KB gzipped (budget ${budget} KB)`,
  )
  if (!ok) failed = true
}
process.exit(failed ? 1 : 0)
