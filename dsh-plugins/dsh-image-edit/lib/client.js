/**
 * dsh-image-edit — browser half.
 *
 * Loader-wrapped lazy CJS, the shape the DSH client module table expects: the
 * script only REGISTERS a factory; the body runs on first import.
 *
 * What it does: registers TWO buttons into the `sidebar.footer.action` slot.
 *   · 改图  — opens the local mask-edit server (http://127.0.0.1:8000) in a new tab.
 *   · 图片  — opens that same local server's `/gallery` page: a grid of the
 *             workspace's images, newest first, click a thumbnail for the原图.
 *
 * Why a gallery on the local server (and not in this half): the GUI's own
 * "produced files" list is derived ONLY from `write` / `edit` / mutating
 * `str_replace_editor` call arguments (see dsh-client-ui-deliverables types:
 * "Reads, unsupported tools, malformed calls, and failed results contribute
 * nothing"). This project's images are produced by scripts, so a bare image
 * path in prose never becomes a clickable link. The local server can read the
 * filesystem, so it builds the listing itself.
 *
 * Contract notes (verified against the shipped packages, not assumed):
 *  - `sidebar.footer.action` owner props are `{ wide: boolean }` only
 *    (`renderSlot("sidebar.footer.action", { wide })` in dsh-client-ui-sidebar).
 *  - `ctx.slots.inject(name, cb)` runs `cb` once the slot exists; inside it,
 *    `ctx.slots.register({ name, id, locale?, inject? }, Component)` returns a
 *    disposer. Distinct `id`s are required for two entries in one slot.
 *  - `inject` must await only services that exist, otherwise the entry pends
 *    forever. `slots` is all this plugin needs.
 *
 * Failure policy: `apply` wraps everything in try/catch. A throw here fails the
 * whole web-shell boot, so this file must never propagate an error.
 */
window.__ModuleLoader__.load({
	id: 'dsh-image-edit',
	factory: (require) => {
		var module = { exports: {} }
		var exports = module.exports
		Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })
		let react = require('react')
		let react_jsx_runtime = require('react/jsx-runtime')

		const SLOT = 'sidebar.footer.action'
		const DEFAULT_URL = 'http://127.0.0.1:8000'
		/** Same-origin route registered by this plugin's node half. */
		const ENSURE_PATH = '/dsh-image-edit/ensure'

		/** Inline SVG: no icon dependency, no external asset to resolve. */
		function Icon(props) {
			return react_jsx_runtime.jsx('svg', {
				width: props.size || 16,
				height: props.size || 16,
				viewBox: '0 0 24 24',
				fill: 'none',
				stroke: 'currentColor',
				strokeWidth: 2,
				strokeLinecap: 'round',
				strokeLinejoin: 'round',
				'aria-hidden': 'true',
				children: [
					react_jsx_runtime.jsx('rect', { key: 'a', x: 3, y: 3, width: 18, height: 18, rx: 2 }),
					react_jsx_runtime.jsx('circle', { key: 'b', cx: 8.5, cy: 8.5, r: 1.5 }),
					react_jsx_runtime.jsx('path', { key: 'c', d: 'M21 15l-5-5L5 21' })
				]
			})
		}

		/** Grid glyph for the gallery entry. */
		function GridIcon(props) {
			return react_jsx_runtime.jsx('svg', {
				width: props.size || 16,
				height: props.size || 16,
				viewBox: '0 0 24 24',
				fill: 'none',
				stroke: 'currentColor',
				strokeWidth: 2,
				strokeLinecap: 'round',
				strokeLinejoin: 'round',
				'aria-hidden': 'true',
				children: [
					react_jsx_runtime.jsx('rect', { key: 'a', x: 3, y: 3, width: 7, height: 7, rx: 1 }),
					react_jsx_runtime.jsx('rect', { key: 'b', x: 14, y: 3, width: 7, height: 7, rx: 1 }),
					react_jsx_runtime.jsx('rect', { key: 'c', x: 3, y: 14, width: 7, height: 7, rx: 1 }),
					react_jsx_runtime.jsx('rect', { key: 'd', x: 14, y: 14, width: 7, height: 7, rx: 1 })
				]
			})
		}

		/**
		 * Ask the node half to bring the local server up, then open `subpath`.
		 *
		 * Graceful degradation: if the route is absent (a DSH process still
		 * running an older node half, which needs a `dsh web` restart to pick
		 * this up), the fetch fails or returns non-JSON, and we fall back to
		 * opening the URL anyway. A 404 from the SPA fallback is therefore NOT
		 * an error the user needs to see.
		 */
		function makeFooterAction(options) {
			const opts = options || {}
			const label0 = opts.label || '改图'
			const subpath = opts.subpath || ''
			const Glyph = opts.icon || Icon

			return function FooterAction(props) {
				const p = props || {}
				const wide = p.wide !== false
				const [state, setState] = react.useState('idle')   // idle | starting | error
				const [message, setMessage] = react.useState('')

				const label = state === 'starting'
					? '启动中…'
					: state === 'error'
						? (label0 + '（启动失败，悬停看原因）')
						: label0

				const open = react.useCallback(async (event) => {
					if (event && event.preventDefault) event.preventDefault()
					if (state === 'starting') return
					setState('starting')
					setMessage('')

					let payload = null
					let routeAnswered = false
					try {
						const res = await fetch(ENSURE_PATH, {
							method: 'POST',
							headers: { Accept: 'application/json' },
							cache: 'no-store',
						})
						// Any JSON body proves the route exists; only then is a
						// failure the user's to see.
						const text = await res.text()
						try { payload = JSON.parse(text); routeAnswered = true } catch (_) { payload = null }
					} catch (error) {
						console.warn('[dsh-image-edit] ensure request failed', error)
					}

					const base = (payload && typeof payload.url === 'string' && payload.url)
						|| DEFAULT_URL
					const target = base.replace(/\/+$/, '') + subpath

					if (payload && payload.ok) {
						setState('idle')
						window.open(target, '_blank', 'noopener,noreferrer')
						return
					}

					if (routeAnswered) {
						// the server could not be started: show why, do not open a
						// page that is guaranteed to be a connection error
						const why = payload.message || '未知原因'
						setState('error')
						setMessage(why)
						console.warn('[dsh-image-edit] ensure refused:', why)
						return
					}

					// route absent (older node half) -> behave exactly as before
					setState('idle')
					window.open(target, '_blank', 'noopener,noreferrer')
				}, [state])

				return react_jsx_runtime.jsxs('button', {
					type: 'button',
					onClick: open,
					disabled: state === 'starting',
					title: message
						? (label + '\n' + message + '\n\n' + ENSURE_PATH)
						: (label + '  →  ' + DEFAULT_URL + subpath + '\n（点击时自动启动本地服务）'),
					'aria-label': label,
					style: {
						display: 'inline-flex',
						alignItems: 'center',
						gap: '6px',
						width: wide ? 'auto' : '28px',
						height: '28px',
						padding: wide ? '0 8px' : '0',
						justifyContent: wide ? 'flex-start' : 'center',
						background: 'transparent',
						border: '1px solid transparent',
						borderRadius: '6px',
						color: state === 'error' ? '#ff6b6b' : 'inherit',
						cursor: state === 'starting' ? 'progress' : 'pointer',
						font: 'inherit',
						opacity: state === 'starting' ? 0.5 : 0.85
					},
					children: [
						react_jsx_runtime.jsx(Glyph, { key: 'i', size: 16 }),
						wide
							? react_jsx_runtime.jsx('span', { key: 't', children: label })
							: null
					]
				})
			}
		}

		/** The two entries, in sidebar order. */
		const ENTRIES = [
			{ id: 'image-edit', label: '改图', subpath: '', icon: Icon },
			{ id: 'image-gallery', label: '图片', subpath: '/gallery', icon: GridIcon },
		]

		/** Cordis service names that must exist before apply runs. */
		const inject = ['slots']

		function apply(ctx) {
			try {
				if (!ctx || !ctx.slots || typeof ctx.slots.inject !== 'function') {
					console.warn('[dsh-image-edit] slots service unavailable; widget not mounted')
					return
				}
				const disposers = []
				ctx.slots.inject(SLOT, () => {
					for (const entry of ENTRIES) {
						try {
							const dispose = ctx.slots.register(
								{ name: SLOT, id: entry.id },
								makeFooterAction(entry)
							)
							disposers.push(dispose)
						} catch (error) {
							console.error('[dsh-image-edit] slot registration failed', entry.id, error)
						}
					}
				})
				return () => {
					for (const dispose of disposers.splice(0)) {
						try {
							if (typeof dispose === 'function') dispose()
						} catch (error) {
							console.error('[dsh-image-edit] dispose failed', error)
						}
					}
				}
			} catch (error) {
				// Never let a widget take the GUI down.
				console.error('[dsh-image-edit] apply failed', error)
			}
		}

		exports.apply = apply
		exports.inject = inject
		return module.exports
	}
})
