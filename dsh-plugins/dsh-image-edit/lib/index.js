/**
 * dsh-image-edit — node half.
 *
 * Two jobs:
 *   1. (unchanged) be a mountable package row so the browser half gets scanned.
 *   2. (new) own the lazy start of the local mask-edit server, so the GUI's
 *      「改图」 button can bring it up on demand instead of requiring the user to
 *      keep a terminal window running.
 *
 * How the two halves talk: this half registers named routes on the injected
 * WebServer; the browser half fetches them on the same origin as the GUI page.
 *   POST <routePath>/ensure  -> probe; spawn if down; wait until it answers
 *   GET  <routePath>/status  -> { running, url, label, pid }
 *   POST <routePath>/stop    -> terminate the pid this plugin started
 *
 * Why spawn detached instead of ctx.subprocess: the subprocess seam terminates
 * every managed process when its service disposes, so the server would die with
 * DSH. This server should outlive a DSH restart, so it is spawned into its own
 * process group, with stdio ignored and unref'd.
 *
 * Verified APIs (read from the shipped packages, not assumed):
 *   - ctx.webServer.register({ kind, path, handler }) -> disposer, and
 *     ctx.effect(() => register(...), name) is the shipped usage pattern
 *     (dsh-webhook-github/lib/index.js).
 *   - the /api browser-trust fence in dsh-client-connection owns ONLY the /api
 *     prefix, so a plugin route outside it is reachable from the same-origin
 *     GUI page.
 *
 * NOTE: changing this file requires restarting `dsh web` — node halves load once
 * at boot. The browser half alone needs only a page reload.
 *
 * Failure policy: this must never throw. A throw here fails the whole web-shell
 * boot, so every entry point is defensive and clamps to defaults.
 */
import { spawn } from 'node:child_process'
import { existsSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs'
import { request as httpRequest } from 'node:http'
import { join } from 'node:path'

export const name = 'image-edit'

/** Cordis services that must exist before apply runs. */
export const inject = ['webServer']

const DEFAULTS = {
  url: 'http://127.0.0.1:8000',
  label: '改图',
  routePath: '/dsh-image-edit',
  port: 8000,
  python: 'C:\\Python314\\python.exe',
  serverScript: 'C:\\Users\\typ\\Desktop\\mantu\\compose\\images\\mask_edit_app.py',
  serverCwd: 'C:\\Users\\typ\\Desktop\\mantu\\compose\\images',
  logFile: 'server.log',
  startTimeoutMs: 25000,
}

/** Never trust config shape: clamp each key to its default instead of throwing. */
function readConfig(raw) {
  const c = Object.assign({}, DEFAULTS, (raw && typeof raw === 'object') ? raw : {})
  const str = (v, d) => (typeof v === 'string' && v.trim() !== '' ? v.trim() : d)
  const routePath = str(c.routePath, DEFAULTS.routePath)
  return {
    url: str(c.url, DEFAULTS.url).replace(/\/+$/, ''),
    label: str(c.label, DEFAULTS.label),
    routePath: routePath.startsWith('/') ? routePath.replace(/\/+$/, '') : DEFAULTS.routePath,
    port: Number.isInteger(c.port) && c.port > 0 && c.port < 65536 ? c.port : DEFAULTS.port,
    python: str(c.python, DEFAULTS.python),
    serverScript: str(c.serverScript, DEFAULTS.serverScript),
    serverCwd: str(c.serverCwd, DEFAULTS.serverCwd),
    logFile: str(c.logFile, DEFAULTS.logFile),
    startTimeoutMs: Number.isFinite(c.startTimeoutMs) && c.startTimeoutMs > 1000
      ? Math.min(c.startTimeoutMs, 120000)
      : DEFAULTS.startTimeoutMs,
  }
}

function sendJson(res, code, obj) {
  try {
    const body = Buffer.from(JSON.stringify(obj), 'utf8')
    res.writeHead(code, {
      'Content-Type': 'application/json; charset=utf-8',
      'Content-Length': String(body.length),
      'Cache-Control': 'no-store',
    })
    res.end(body)
  } catch {
    try { res.destroy() } catch { /* already gone */ }
  }
}

/**
 * Is something already answering on the configured url?
 *
 * DELIBERATELY NOT fetch() + AbortController. Measured on this machine (Node
 * v24.18.0, 2026-09-18): aborting a fetch mid-flight against a server that
 * answers over HTTP/1.0 throws an UNCAUGHT assertion inside undici
 * (`AssertionError: assert(!this.paused)` at Parser.finish), which kills the
 * whole process — and it is not catchable, because it is thrown from a socket
 * event handler. This plugin runs inside the DSH host process, so that would
 * take the entire GUI down. node:http's own client has no such path, and
 * `req.destroy()` on timeout is its documented cancellation.
 */
function probe(url, timeoutMs = 1500) {
  return new Promise((resolve) => {
    let settled = false
    const finish = (v) => { if (!settled) { settled = true; resolve(v) } }
    let req
    try {
      req = httpRequest(url + '/', { method: 'GET', timeout: timeoutMs }, (res) => {
        res.resume()                       // drain so the socket closes cleanly
        finish(res.statusCode >= 200 && res.statusCode < 400)
      })
    } catch {
      return finish(false)
    }
    req.on('timeout', () => { try { req.destroy() } catch { /* ignore */ } finish(false) })
    req.on('error', () => finish(false))
    req.end()
  })
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/** Poll until the server answers, or the deadline passes. */
async function waitUntilUp(url, timeoutMs, stepMs = 400) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await probe(url)) return true
    await sleep(stepMs)
  }
  return probe(url)
}

async function waitUntilDown(url, timeoutMs, stepMs = 300) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (!(await probe(url, 800))) return true
    await sleep(stepMs)
  }
  return !(await probe(url, 800))
}

/**
 * Register the routes. `startedPid` tracks what THIS process spawned; the
 * pidfile carries it across a DSH restart so /stop still works afterwards.
 */
function registerRoutes(ctx, cfg, log) {
  const pidFile = join(cfg.serverCwd, '.dsh-image-edit.pid')
  let startedPid = 0

  const readPid = () => {
    if (startedPid) return startedPid
    try {
      const n = Number.parseInt(readFileSync(pidFile, 'utf8').trim(), 10)
      return Number.isInteger(n) && n > 0 ? n : 0
    } catch {
      return 0
    }
  }
  const writePid = (pid) => {
    try { writeFileSync(pidFile, String(pid), 'utf8') } catch { /* non-fatal */ }
  }
  const clearPid = () => {
    try { unlinkSync(pidFile) } catch { /* already gone */ }
  }

  const ensure = async (req, res) => {
    try {
      if (await probe(cfg.url)) {
        return sendJson(res, 200, {
          ok: true, running: true, started: false,
          url: cfg.url, label: cfg.label, pid: readPid() || null,
        })
      }

      const missing = []
      if (!existsSync(cfg.python)) missing.push(`python: ${cfg.python}`)
      if (!existsSync(cfg.serverScript)) missing.push(`服务脚本: ${cfg.serverScript}`)
      if (missing.length) {
        return sendJson(res, 503, {
          ok: false, running: false, started: false, url: cfg.url,
          message: '找不到启动所需的文件：\n' + missing.join('\n'),
        })
      }

      log(`starting: ${cfg.python} ${cfg.serverScript} --port ${cfg.port}`)
      let spawnError = ''
      const child = spawn(
        cfg.python,
        [cfg.serverScript, '--port', String(cfg.port), '--log', cfg.logFile],
        { cwd: cfg.serverCwd, detached: true, stdio: 'ignore', windowsHide: true },
      )
      child.on('error', (e) => { spawnError = String((e && e.message) || e) })
      child.unref()
      startedPid = child.pid || 0
      if (startedPid) writePid(startedPid)

      const t0 = Date.now()
      const up = await waitUntilUp(cfg.url, cfg.startTimeoutMs)
      const waitedMs = Date.now() - t0

      if (!up) {
        return sendJson(res, 503, {
          ok: false, running: false, started: true, pid: startedPid || null,
          url: cfg.url, waitedMs,
          message: spawnError
            ? `启动失败：${spawnError}`
            : `已发出启动命令，但 ${waitedMs} ms 内 ${cfg.url} 仍未响应。\n`
              + `请查看日志：${join(cfg.serverCwd, cfg.logFile)}`,
        })
      }

      log(`up after ${waitedMs} ms (pid ${startedPid})`)
      return sendJson(res, 200, {
        ok: true, running: true, started: true, pid: startedPid || null,
        url: cfg.url, label: cfg.label, waitedMs,
      })
    } catch (e) {
      return sendJson(res, 500, { ok: false, url: cfg.url, message: String((e && e.message) || e) })
    }
  }

  const status = async (req, res) => {
    try {
      const running = await probe(cfg.url)
      return sendJson(res, 200, {
        ok: true, running, url: cfg.url, label: cfg.label,
        pid: readPid() || null, python: cfg.python, script: cfg.serverScript,
      })
    } catch (e) {
      return sendJson(res, 500, { ok: false, message: String((e && e.message) || e) })
    }
  }

  const stop = async (req, res) => {
    try {
      const pid = readPid()
      if (!pid) {
        return sendJson(res, 409, {
          ok: false, running: await probe(cfg.url),
          message: '没有记录到本插件启动的进程号（服务可能是你手动启动的，请手动关闭）。',
        })
      }
      let killError = ''
      try {
        process.kill(pid)
      } catch (e) {
        killError = String((e && e.message) || e)
      }
      const down = await waitUntilDown(cfg.url, 8000)
      if (down) clearPid()
      startedPid = 0
      return sendJson(res, down ? 200 : 500, {
        ok: down, running: !down, pid, killed: killError === '',
        message: down ? '已停止。' : (killError || '发出终止信号后服务仍在响应。'),
      })
    } catch (e) {
      return sendJson(res, 500, { ok: false, message: String((e && e.message) || e) })
    }
  }

  const disposers = []
  const routes = [
    { kind: 'exact', path: `${cfg.routePath}/ensure`, handler: ensure },
    { kind: 'exact', path: `${cfg.routePath}/status`, handler: status },
    { kind: 'exact', path: `${cfg.routePath}/stop`, handler: stop },
  ]
  for (const route of routes) {
    try {
      disposers.push(ctx.webServer.register(route))
      log(`route registered: ${route.path}`)
    } catch (e) {
      log(`route registration failed for ${route.path}: ${e}`)
    }
  }
  return () => {
    for (const dispose of disposers.splice(0)) {
      try { if (typeof dispose === 'function') dispose() } catch { /* ignore */ }
    }
  }
}

export function apply(ctx, config = {}) {
  try {
    const cfg = readConfig(config)
    const log = (msg) => {
      try { ctx?.logger?.info?.(`[dsh-image-edit] ${msg}`) } catch { /* ignore */ }
    }
    log(`tool url: ${cfg.url} (label: ${cfg.label})`)

    if (!ctx || !ctx.webServer || typeof ctx.webServer.register !== 'function') {
      log('webServer service unavailable; lazy-start routes not mounted')
      return
    }

    try {
      ctx.effect(
        () => registerRoutes(ctx, cfg, log),
        'image-edit: lazy-start routes',
      )
    } catch (e) {
      log(`route effect failed: ${e}`)
    }
  } catch (error) {
    // Never let a widget take the GUI down.
    try { console.error('[dsh-image-edit] apply failed', error) } catch { /* ignore */ }
  }
}

/** Exported for the offline harness in _test_lazy_start.mjs — not part of the plugin API. */
export const __test = { readConfig, probe, waitUntilUp, registerRoutes, sendJson }
