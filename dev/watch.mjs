#!/usr/bin/env node
/*
 * One-command hot-reload loop for the full weewx pipeline.
 *
 * Watches the skin and its supporting Python search-list, rebuilds the
 * front-end, regenerates the weewx report, and live-reloads the browser -
 * so any change to skins/Nordlys/, bin/user/nordlys/, or src/ is reflected
 * without running anything by hand.
 *
 * Usage: node dev/watch.mjs [port]     (default 8123)
 * Prereq: dev/setup.py has been run and .venv has weewx installed.
 *
 * The live-reload snippet is injected only into served HTML responses; the
 * committed skin files and the generated public_html/ are never modified.
 *
 * Note: fs.watch({recursive:true}) is native on macOS/Windows; on Linux it
 * needs Node 20+.
 */

import { spawn } from 'node:child_process'
import { createReadStream, existsSync, watch } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname, join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO_ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const PORT = Number(process.argv[2] ?? 8123)
const CONFIG = 'dev/weewx/weewx.conf'
const WEECTL = join(REPO_ROOT, '.venv', 'bin', 'weectl')
const PUBLIC_DIR = join(REPO_ROOT, 'dev', 'weewx', 'public_html', 'nordlys')

// Repo source dirs whose changes affect the generated report.
const WATCH_DIRS = [
  join(REPO_ROOT, 'skins', 'Nordlys'), // templates, skin.conf, css, dist/
  join(REPO_ROOT, 'bin', 'user', 'nordlys'), // Python search-list extension
]

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
}

// --- live-reload client, injected into served HTML only --------------------
const RELOAD_SNIPPET = `<script>
(function () {
  const es = new EventSource('/__reload')
  es.addEventListener('reload', () => location.reload())
})()
</script>`

const clients = new Set()

function broadcastReload() {
  for (const res of clients) res.write('event: reload\ndata: 1\n\n')
}

// --- static server with SSE + HTML injection -------------------------------
const server = createServer(async (req, res) => {
  if (req.url === '/__reload') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    })
    res.write('retry: 1000\n\n')
    clients.add(res)
    req.on('close', () => clients.delete(res))
    return
  }

  let path = decodeURIComponent(req.url.split('?')[0])
  if (path.endsWith('/')) path += 'index.html'
  const file = join(PUBLIC_DIR, path)

  // Contain traversal to the served directory.
  if (!file.startsWith(PUBLIC_DIR) || !existsSync(file)) {
    res.writeHead(404, { 'Content-Type': 'text/plain' })
    res.end('404 Not Found')
    return
  }

  const ext = extname(file)
  const type = MIME[ext] ?? 'application/octet-stream'

  if (ext === '.html') {
    let html = await readFile(file, 'utf8')
    html = html.includes('</body>')
      ? html.replace('</body>', `${RELOAD_SNIPPET}</body>`)
      : html + RELOAD_SNIPPET
    res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' })
    res.end(html)
    return
  }

  res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' })
  createReadStream(file).pipe(res)
})

// --- report regeneration (debounced, non-overlapping) ----------------------
let timer = null
let running = false
let pending = false

function scheduleReport() {
  clearTimeout(timer)
  timer = setTimeout(runReport, 300)
}

function runReport() {
  if (running) {
    pending = true
    return
  }
  running = true
  const started = process.hrtime.bigint()
  const child = spawn(
    WEECTL,
    ['report', 'run', '--config', CONFIG],
    { cwd: REPO_ROOT, stdio: ['ignore', 'ignore', 'inherit'] },
  )
  child.on('exit', (code) => {
    running = false
    if (code === 0) {
      const ms = Number(process.hrtime.bigint() - started) / 1e6
      console.log(`[watch] report regenerated in ${ms.toFixed(0)}ms -> reload`)
      broadcastReload()
    } else {
      console.error(`[watch] report run failed (exit ${code})`)
    }
    if (pending) {
      pending = false
      scheduleReport()
    }
  })
}

// --- start everything ------------------------------------------------------
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(
      `[watch] port ${PORT} is already in use. Stop the other server or ` +
        `pass a free port: npm run dev:weewx -- <port>`,
    )
  } else {
    console.error(`[watch] server error: ${err.message}`)
  }
  process.exit(1)
})
server.listen(PORT, () => {
  console.log(`[watch] serving http://localhost:${PORT} (live reload)`)
})

// Rebuild the front-end on src/ changes; dist/ writes land under skins/Nordlys/
// and are picked up by the source watcher below.
const vite = spawn('npx', ['vite', 'build', '--watch'], {
  cwd: REPO_ROOT,
  stdio: ['ignore', 'inherit', 'inherit'],
})

for (const dir of WATCH_DIRS) {
  if (!existsSync(dir)) continue
  watch(dir, { recursive: true }, scheduleReport)
}

console.log('[watch] watching skins/Nordlys, bin/user/nordlys, and src (via vite)')

// Initial report so the served page is fresh on startup.
scheduleReport()

function shutdown() {
  vite.kill()
  server.close()
  process.exit(0)
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
