/**
 * Offline harness for the dsh-image-edit node half.
 *
 * It cannot boot Cordis, so it fakes the minimum the plugin touches
 * (webServer.register / ctx.effect / logger), captures the registered routes,
 * then calls them with fake req/res objects — and really does start and stop the
 * local mask-edit server through that path. That is the only way to prove the
 * lazy start works without restarting the GUI.
 *
 * Run:  node _test_lazy_start.mjs
 */
import { execFileSync } from 'node:child_process'
import { apply, __test } from './dsh-image-edit/lib/index.js'

const URL_BASE = 'http://127.0.0.1:8000'
const FAILS = []
function check(cond, label, detail) {
  console.log((cond ? '  PASS  ' : '  FAIL  ') + label + (detail ? '  ' + detail : ''))
  if (!cond) FAILS.push(label)
}

// ---------------------------------------------------------------- fake ctx
const routes = new Map()
const logs = []
const ctx = {
  logger: { info: (m) => logs.push(m), warn: (m) => logs.push(m) },
  webServer: {
    register(route) {
      if (routes.has(route.path)) throw new Error('duplicate route ' + route.path)
      routes.set(route.path, route)
      return () => routes.delete(route.path)
    },
  },
  effect(fn, name) { fn(); return () => {} },
}

function fakeRes() {
  const res = {
    code: 0, body: '', headers: {},
    writeHead(code, headers) { res.code = code; Object.assign(res.headers, headers || {}) },
    end(b) { res.body = b ? Buffer.from(b).toString('utf8') : '' },
    destroy() {},
  }
  return res
}

async function call(path, method = 'POST') {
  const route = routes.get(path)
  if (!route) throw new Error('no route ' + path)
  const res = fakeRes()
  await route.handler({ method, url: path }, res)
  let json = null
  try { json = JSON.parse(res.body) } catch { /* keep null */ }
  return { code: res.code, json, raw: res.body }
}

async function alive() {
  // use the plugin's own probe: fetch()+abort is unsafe here (see probe's note),
  // and the harness must not crash on the very thing it is testing around.
  return __test.probe(URL_BASE, 1500)
}

console.log('=== 0. mount ===')
apply(ctx, {})
check(routes.size === 3, 'registered 3 routes', [...routes.keys()].join(' '))
check(routes.has('/dsh-image-edit/ensure'), 'has /ensure')
check(routes.has('/dsh-image-edit/status'), 'has /status')
check(routes.has('/dsh-image-edit/stop'), 'has /stop')

console.log('\n=== 1. status while the server is DOWN ===')
// make sure we start from a known state: kill anything listening on 8000
try {
  const out = execFileSync('powershell', ['-NoProfile', '-Command',
    "(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess"],
    { encoding: 'utf8' }).trim()
  for (const pid of out.split(/\s+/).filter(Boolean)) {
    try { process.kill(Number(pid)); console.log(`  (stopped pre-existing pid ${pid})`) } catch { /* ignore */ }
  }
} catch { /* nothing listening */ }
await new Promise((r) => setTimeout(r, 1500))
check(!(await alive()), 'precondition: nothing on ' + URL_BASE)

let r = await call('/dsh-image-edit/status', 'GET')
check(r.code === 200 && r.json?.running === false, 'status says running=false',
  JSON.stringify(r.json))

console.log('\n=== 2. ensure -> must actually start it ===')
const t0 = Date.now()
r = await call('/dsh-image-edit/ensure')
const took = Date.now() - t0
check(r.code === 200 && r.json?.ok === true, 'ensure returned ok',
  `HTTP ${r.code} ${JSON.stringify(r.json).slice(0, 160)}`)
check(r.json?.started === true, 'ensure reports started=true')
check(Number.isInteger(r.json?.pid) && r.json.pid > 0, 'ensure reports a pid', String(r.json?.pid))
check(await alive(), 'the server really answers now', `took ${took} ms`)
const firstPid = r.json?.pid

console.log('\n=== 3. ensure again is idempotent ===')
r = await call('/dsh-image-edit/ensure')
check(r.code === 200 && r.json?.running === true && r.json?.started === false,
  'second ensure: running=true, started=false', JSON.stringify(r.json))
check(r.json?.pid === firstPid, 'pid unchanged (no second process)', `${r.json?.pid} vs ${firstPid}`)

console.log('\n=== 4. status while UP ===')
r = await call('/dsh-image-edit/status', 'GET')
check(r.json?.running === true, 'status says running=true')
check(r.json?.url === URL_BASE, 'status reports the configured url', r.json?.url)

console.log('\n=== 5. stop ===')
r = await call('/dsh-image-edit/stop')
check(r.code === 200 && r.json?.ok === true, 'stop returned ok', JSON.stringify(r.json))
check(!(await alive()), 'the server is really down now')
r = await call('/dsh-image-edit/status', 'GET')
check(r.json?.running === false, 'status says running=false after stop')

console.log('\n=== 6. bad config must not throw ===')
try {
  apply({ ...ctx, webServer: undefined }, {})
  check(true, 'apply tolerates a missing webServer service')
} catch (e) {
  check(false, 'apply tolerates a missing webServer service', String(e))
}
try {
  const cfg = { url: 42, port: -1, routePath: 'nonsense', startTimeoutMs: 'soon' }
  const fake = { ...ctx, webServer: { register: () => () => {} } }
  apply(fake, cfg)
  check(true, 'apply tolerates a garbage config object')
} catch (e) {
  check(false, 'apply tolerates a garbage config object', String(e))
}

console.log('\n=== 7. disposal removes every route (no leak on reload) ===')
{
  const routes2 = new Map()
  let disposer = null
  const ctx2 = {
    logger: { info: () => {} },
    webServer: {
      register(route) { routes2.set(route.path, route); return () => routes2.delete(route.path) },
    },
    effect(fn) { disposer = fn(); return () => {} },
  }
  apply(ctx2, {})
  check(routes2.size === 3, 'second mount registered 3 routes', String(routes2.size))
  check(typeof disposer === 'function', 'the effect callback returned a disposer')
  if (typeof disposer === 'function') disposer()
  check(routes2.size === 0, 'disposer removed every route', String(routes2.size))
}

console.log('\n=== server log lines captured ===')
logs.slice(0, 8).forEach((l) => console.log('  ' + l))

console.log('\n' + '='.repeat(56))
console.log('FAILED: ' + FAILS.length + (FAILS.length ? '  ' + JSON.stringify(FAILS) : ' (all passed)'))
console.log('='.repeat(56))
process.exit(FAILS.length ? 1 : 0)
