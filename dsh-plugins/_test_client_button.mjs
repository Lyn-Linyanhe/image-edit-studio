/**
 * Offline harness for the dsh-image-edit browser half.
 *
 * The client file is a loader-wrapped lazy CJS bundle, so it is executed in a vm
 * with a fake `window.__ModuleLoader__`, a fake `require` (React + jsx-runtime),
 * and a recording `fetch` / `window.open`. Then the button's onClick is invoked
 * and the resulting calls are asserted.
 *
 * What it pins down — the click must START the server through the same-origin
 * route before opening the page, and must not confuse "route absent" with
 * "route said no":
 *   1. ok:true                 -> opens the url the route returned
 *   2. ok:false (start failed) -> does NOT open; button shows the error
 *   3. fetch throws (no route) -> falls back to opening DEFAULT_URL
 *   4. non-JSON body           -> falls back to opening DEFAULT_URL
 *
 * Run:  node _test_client_button.mjs
 */
import { readFileSync } from 'node:fs'
import { createContext, runInContext } from 'node:vm'

const FAILS = []
function check(cond, label, detail) {
  console.log((cond ? '  PASS  ' : '  FAIL  ') + label + (detail ? '  ' + detail : ''))
  if (!cond) FAILS.push(label)
}

const SRC = readFileSync('./dsh-image-edit/lib/client.js', 'utf8')

// --------------------------------------------------------------- fake React
function makeReact() {
  const states = []
  let cursor = 0
  return {
    __reset() { cursor = 0 },
    __states: states,
    useState(init) {
      const i = cursor++
      if (!(i in states)) states[i] = init
      return [states[i], (v) => {
        states[i] = typeof v === 'function' ? v(states[i]) : v
      }]
    },
    useCallback(fn) { return fn },
  }
}

function makeJsx() {
  const build = (type, props) => {
    const { children, ...rest } = props || {}
    return { type, props: { ...rest, children } }
  }
  return { jsx: build, jsxs: build, Fragment: 'Fragment' }
}

/** Load the client bundle and return its exported module. */
function loadClient(react, jsxRuntime) {
  let captured = null
  const sandbox = {
    window: {
      __ModuleLoader__: { load: (def) => { captured = def } },
      open: (...args) => sandbox.__opened.push(args),
    },
    console,
    setTimeout,
    clearTimeout,
    __opened: [],
  }
  sandbox.globalThis = sandbox
  const ctx = createContext(sandbox)
  runInContext(SRC, ctx, { filename: 'client.js' })
  if (!captured) throw new Error('client never registered a module')
  // the factory itself returns module.exports
  const exportsObj = captured.factory((id) => {
    if (id === 'react') return react
    if (id === 'react/jsx-runtime') return jsxRuntime
    throw new Error('unexpected require: ' + id)
  })
  return { mod: exportsObj, sandbox }
}

/** Mount every registered footer component; default target is the 改图 entry. */
function mount(mod, react, wantedId) {
  const comps = new Map()
  const ctx = {
    slots: {
      inject: (name, cb) => cb(),
      register: (meta, comp) => { comps.set((meta && meta.id) || '', comp); return () => {} },
    },
  }
  mod.apply(ctx)
  if (comps.size === 0) throw new Error('component was not registered')
  const id = wantedId || 'image-edit'
  const Component = comps.get(id)
  if (typeof Component !== 'function') {
    throw new Error('component not registered: ' + id + ' (have: ' + [...comps.keys()].join(', ') + ')')
  }
  const render = () => { react.__reset(); return Component({ wide: true }) }
  const tree = render()
  return { tree, render, click: tree.props.onClick, comps }
}

function labelOf(tree) {
  const span = tree.props.children.find((c) => c && c.type === 'span')
  return span ? span.props.children : null
}

// ------------------------------------------------------- scenario harness
async function scenario(name, fetchImpl, assertions, componentId) {
  const react = makeReact()
  const { mod, sandbox } = loadClient(react, makeJsx())
  sandbox.fetch = fetchImpl
  const { tree, render, click, comps } = mount(mod, react, componentId)
  sandbox.__opened.length = 0

  await click({ preventDefault() {} })
  await new Promise((r) => setTimeout(r, 20))

  console.log(`\n=== ${name} ===`)
  assertions({ opened: sandbox.__opened, tree: render(), fetchCalls: sandbox.__fetchCalls || [], comps })
}

const jsonRes = (obj, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  text: async () => JSON.stringify(obj),
})

// 1. success
await scenario('1. ensure ok -> opens the url the route returned', async (url, opts) => {
  check(String(url).includes('/dsh-image-edit/ensure'), 'fetched the ensure route', String(url))
  check(opts && opts.method === 'POST', 'used POST', String(opts && opts.method))
  return jsonRes({ ok: true, running: true, started: true, url: 'http://127.0.0.1:8000', pid: 1234 })
}, ({ opened, tree }) => {
  check(opened.length === 1, 'opened exactly one tab', JSON.stringify(opened))
  check(opened[0] && opened[0][0] === 'http://127.0.0.1:8000', 'opened the returned url',
    JSON.stringify(opened[0]))
  check(labelOf(tree) === '改图', 'label back to normal', String(labelOf(tree)))
})

// 2. route answered "could not start"
await scenario('2. ensure says start FAILED -> no tab, error shown',
  async () => jsonRes({ ok: false, running: false, message: '找不到启动所需的文件：\npython: X' }, 503),
  ({ opened, tree }) => {
    check(opened.length === 0, 'did NOT open a guaranteed-dead page', JSON.stringify(opened))
    check(/启动失败/.test(String(labelOf(tree))), 'label shows the failure', String(labelOf(tree)))
    check(/找不到启动所需的文件/.test(String(tree.props.title)), 'title carries the reason',
      String(tree.props.title).split('\n')[1] || '')
  })

// 3. route absent -> fetch rejects
await scenario('3. route ABSENT (fetch throws) -> falls back to opening DEFAULT_URL',
  async () => { throw new TypeError('Failed to fetch') },
  ({ opened, tree }) => {
    check(opened.length === 1 && opened[0][0] === 'http://127.0.0.1:8000',
      'fell back to the hard-coded url (old behaviour)', JSON.stringify(opened))
    check(labelOf(tree) === '改图', 'no error state for an absent route', String(labelOf(tree)))
  })

// 4. SPA fallback answered with HTML instead of JSON
await scenario('4. non-JSON answer (SPA fallback) -> falls back to opening DEFAULT_URL',
  async () => ({ ok: true, status: 200, text: async () => '<!doctype html><html>...</html>' }),
  ({ opened, tree }) => {
    check(opened.length === 1 && opened[0][0] === 'http://127.0.0.1:8000',
      'treated a non-JSON body as "route absent"', JSON.stringify(opened))
    check(labelOf(tree) === '改图', 'no error state', String(labelOf(tree)))
  })

console.log('\n' + '='.repeat(56))
console.log('=== 5. 图片按钮：ensure ok -> 打开 /gallery ===')
await scenario('5. 图片 button -> opens <url>/gallery', async () =>
  jsonRes({ ok: true, running: true, started: false, url: 'http://127.0.0.1:8000', pid: 1234 }),
  ({ opened, tree, comps }) => {
    check(opened.length === 1, 'opened exactly one tab', JSON.stringify(opened))
    check(opened[0] && opened[0][0] === 'http://127.0.0.1:8000/gallery',
      'opened the gallery page', JSON.stringify(opened[0]))
    check(labelOf(tree) === '图片', 'label is 图片', String(labelOf(tree)))
    check(String(tree.props.title).includes('/gallery'), 'title mentions /gallery',
      String(tree.props.title).split('\n')[0])
    check(comps.has('image-edit') && comps.has('image-gallery'),
      'BOTH entries registered with distinct ids', [...comps.keys()].join(', '))
  }, 'image-gallery')

console.log('\n=== 6. 图片按钮：route 不存在时回退到默认地址 ===')
await scenario('6. 图片 button, route absent -> falls back to DEFAULT_URL/gallery',
  async () => { throw new TypeError('Failed to fetch') },
  ({ opened, tree }) => {
    check(opened.length === 1 && opened[0][0] === 'http://127.0.0.1:8000/gallery',
      'fell back to the hard-coded url + /gallery', JSON.stringify(opened))
    check(labelOf(tree) === '图片', 'no error state for an absent route', String(labelOf(tree)))
  }, 'image-gallery')

console.log('\n=== 7. 图片按钮：服务起不来时不打开死页面 ===')
await scenario('7. 图片 button, ensure says start FAILED -> no tab, error shown',
  async () => jsonRes({ ok: false, running: false, message: '找不到启动所需的文件：python: X' }, 503),
  ({ opened, tree }) => {
    check(opened.length === 0, 'did NOT open a guaranteed-dead page', JSON.stringify(opened))
    check(/启动失败/.test(String(labelOf(tree))), 'label shows the failure', String(labelOf(tree)))
  }, 'image-gallery')

console.log('\n' + '='.repeat(56))
console.log('FAILED: ' + FAILS.length + (FAILS.length ? '  ' + JSON.stringify(FAILS) : ' (all passed)'))
console.log('='.repeat(56))
process.exit(FAILS.length ? 1 : 0)
