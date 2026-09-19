
// This page may be embedded in a sandboxed iframe (observed: "The document is
// sandboxed and lacks the 'allow-same-origin' flag"), in which case ANY
// localStorage/sessionStorage access THROWS a SecurityError. An uncaught throw
// at top level aborts the whole script, so no click handler ever gets bound and
// the page looks dead. Everything therefore goes through this safe shim.
const mem = {};
const store = {
  get(k) {
    try { const v = localStorage.getItem(k); if (v !== null) return v; } catch (_) {}
    return Object.prototype.hasOwnProperty.call(mem, k) ? mem[k] : null;
  },
  set(k, v) {
    mem[k] = String(v);
    try { localStorage.setItem(k, v); } catch (_) {}
  },
  del(k) {
    delete mem[k];
    try { localStorage.removeItem(k); } catch (_) {}
  },
  get available() {
    try { localStorage.setItem('__t', '1'); localStorage.removeItem('__t'); return true; }
    catch (_) { return false; }
  }
};

window.addEventListener('error', ev => {
  const m = document.getElementById('msg');
  if (m) { m.className = 'msg bad'; m.textContent = '页面脚本错误：' + (ev.message || ev.error); }
});
// If any of this leaks out of the handlers below, show it instead of dying
// silently - the user cannot see the browser console.
window.addEventListener('unhandledrejection', ev => {
  const m = document.getElementById('msg');
  const r = ev.reason;
  if (m) {
    m.className = 'msg bad';
    m.textContent = '未捕获异常：' + ((r && (r.name + ': ' + r.message)) || String(r));
  }
});

const $ = id => document.getElementById(id);

// Absolute base for our own API. The page may be embedded in a sandboxed
// iframe on a different origin, where a relative fetch('/api/...') would go to
// the WRONG host (the parent's origin) and fail. The server substitutes
// __APP_ORIGIN__ with its real address when serving this page.
const APP_ORIGIN = "__APP_ORIGIN__";
const api = path => APP_ORIGIN + path;

// Catch network-level failures that would otherwise never reach the UI. The
// browser console is not visible to the user, so surface them here.
window.addEventListener('unhandledrejection', ev => {
  const m = document.getElementById('msg');
  const r = ev.reason;
  if (m) {
    m.className = 'msg bad';
    m.textContent = '请求异常：' + (r && (r.name + ': ' + r.message) || String(r))
      + '\n目标地址：' + APP_ORIGIN;
  }
});
const cv = $('cv'), ctx = cv.getContext('2d');
let img = null, scale = 1, drawing = false, erase = false, hasMask = false;
let resultURL = null;
// each loaded image keeps its OWN mask canvas, so a batch of images can each be
// painted separately while sharing one prompt and one set of parameters
let films = [];        // {name, im, mc, masked, resultB64}
let active = -1;

// diagnostics for the last upload attempt - shown on failure so the cause is
// visible instead of a bare "generation failed"
const diag = {};
function diagText() {
  const lines = [];
  if (diag.engine) lines.push('引擎：' + diag.engine);
  if (diag.image) lines.push('上传图片：' + diag.image);
  if (diag.refs) lines.push('参考图：' + diag.refs);
  if (diag.mask) lines.push('遮罩：' + diag.mask);
  if (diag.ms != null) lines.push('耗时：' + (diag.ms / 1000).toFixed(1) + ' s');
  lines.push('模型：' + ($('model') ? $('model').value : '?')
    + '　画质：' + ($('quality') ? $('quality').value : '?')
    + '　尺寸：' + ($('size') ? $('size').value : '?'));
  lines.push('本地服务：' + api('/api/edit'));
  return lines.join('\n');
}

// ---- quality <-> size must be a legal pair (per the relay's spec) ----
const SIZES = {
  low:    [['1024x1536','1024x1536 竖幅 2:3'],['1024x1024','1024x1024 方形 1:1'],['1536x1024','1536x1024 横幅 3:2']],
  medium: [['1152x2048','1152x2048 竖幅 9:16'],['2048x2048','2048x2048 方形 1:1'],['2048x1152','2048x1152 横幅 16:9']],
  high:   [['2160x3840','2160x3840 竖幅 9:16'],['2880x2880','2880x2880 方形 1:1'],['3840x2160','3840x2160 横幅 16:9']],
};
let savedSize = store.get('mie_size') || '';

// ---- engines: credentials and size rules differ per engine (all measured) ----
// `mask` / `multiImage` mirror the server's ENGINES table and are used by the
// slot planner below, so the UI can show the real image numbering before a run
// instead of guessing.
// NOTE: a file upload is a BATCH queue (one request per image); the 参考图 list
// is different — those are attached to EVERY request as reference images.
const ENGINE_DEFAULTS = {
  gpt: {
    key: 'sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915',
    model: 'gpt-image-2',
    kind: 'quality',
    mask: true,
    multiImage: true,
    hint: 'GPT Image 2：文生图与图生图都可用；图生图支持「仅涂过的区域」（红色标记参考图 + 指令）。'
        + ' 画质与尺寸必须同档：low=1K / medium=2K / high=4K。'
        + ' 支持多张参考图（最多 4 张图，含内容图与红色标记图）。',
  },
  grok: {
    key: 'sk-4d8246189f69f4f76ec0439a656b089111a4ae63d05f5be0f53d1c56754bdc62',
    model: 'grok-imagine',
    kind: 'resolution',
    mask: false,
    multiImage: false,
    hint: 'Grok Imagine：文生图可用（已强制用 b64 内联返回）。两条实测限制 —— '
        + '① 图生图返回的图片地址在 imgen.x.ai，本机访问不了，会拿不到图；'
        + '② Grok 不支持遮罩，且不接受多于 1 张输入图片（HTTP 400）→ 不能加参考图。'
        + ' 档位用 resolution（1k/2k/4k，4k 上游可能拒绝）。',
  },
};
function currentEngine() {
  return $('engine') ? $('engine').value : 'gpt';
}

// ---- reference images: role-tagged, sent WITH every request ---------------
// NOT batch items. Server side: take_reference_images() + REF_ROLES.
// Send order is always: image (content) -> image[1] red mask guide (if mask
// mode) -> image[2..] these references, in the order added here.
let refs = [];         // {name, im, role}
const MAX_IMAGE_SLOTS_CLIENT = 4;
const REF_ROLES = [
  ['style',   '画法 / 风格', '只取笔触、线稿、明暗、材质；不取内容与配色'],
  ['pose',    '姿态',        '只取人物姿态；不取身份、服装、颜色'],
  ['content', '内容 / 身份', '提供人物身份、五官、发型、服饰与配色'],
  ['other',   '其他',        '按提示词里的说明使用'],
];
const SLOT_LABEL_CONTENT = '要改的内容图（身份与颜色的唯一来源）';
const SLOT_LABEL_MASK = '红色标记图（涂红区域 = 唯一允许改动的地方）';

function engFlags() {
  const d = ENGINE_DEFAULTS[currentEngine()] || ENGINE_DEFAULTS.gpt;
  return { mask: !!d.mask, multi: !!d.multiImage };
}
function wholeScope() { return $('scope') ? $('scope').value === 'whole' : true; }
function maskSlotUsed() { const f = engFlags(); return f.mask && !wholeScope(); }

/** What this request will actually contain, in send order. */
function slotPlan() {
  const plan = [{ n: 1, label: SLOT_LABEL_CONTENT }];
  if (maskSlotUsed()) plan.push({ n: 2, label: SLOT_LABEL_MASK });
  const first = maskSlotUsed() ? 3 : 2;
  refs.forEach((r, i) => {
    const role = REF_ROLES.find(x => x[0] === r.role) || REF_ROLES[3];
    plan.push({ n: first + i, label: '参考图 · ' + role[1] + '（' + r.name + '）' });
  });
  return plan;
}
function maxRefsNow() {
  const used = 1 + (maskSlotUsed() ? 1 : 0);
  return Math.max(0, MAX_IMAGE_SLOTS_CLIENT - used);
}

function renderRefs() {
  const box = $('refList');
  if (!box) return;
  box.innerHTML = '';
  const plan = slotPlan();
  const first = plan.length - refs.length;   // index of this ref's first slot
  refs.forEach((r, i) => {
    const slot = plan[first + i];
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:8px;margin-top:8px;'
      + 'padding:6px;border:1px solid var(--line);border-radius:6px';

    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:relative;width:52px;height:52px;flex:none';
    const t = document.createElement('img');
    t.src = r.im.src;
    t.style.cssText = 'width:52px;height:52px;object-fit:cover;border-radius:4px;display:block';
    wrap.appendChild(t);
    // the number this image occupies inside every request — shown ON the thumb
    const tb = document.createElement('span');
    tb.className = 'slot';
    tb.textContent = slot ? ('图' + slot.n) : '—';
    wrap.appendChild(tb);
    row.appendChild(wrap);

    const badge = document.createElement('span');
    badge.className = 'pill';
    badge.textContent = slot ? ('图' + slot.n) : '—';
    badge.title = '这张图在请求里的编号（会自动写进提示词）';
    row.appendChild(badge);

    const info = document.createElement('div');
    info.style.cssText = 'flex:1;min-width:0';
    const nm = document.createElement('div');
    nm.textContent = r.name;
    nm.style.cssText = 'font-size:11px;color:var(--dim);white-space:nowrap;'
      + 'overflow:hidden;text-overflow:ellipsis';
    info.appendChild(nm);

    const sel = document.createElement('select');
    sel.style.cssText = 'font-size:12px;padding:4px;width:100%;margin-top:3px';
    REF_ROLES.forEach(([v, label, desc]) => {
      const o = document.createElement('option');
      o.value = v; o.textContent = label; o.title = desc;
      if (r.role === v) o.selected = true;
      sel.appendChild(o);
    });
    sel.onchange = () => { r.role = sel.value; renderSlotPreview(); };
    info.appendChild(sel);
    row.appendChild(info);

    const del = document.createElement('button');
    del.textContent = '移除';
    del.style.cssText = 'flex:none';
    del.onclick = () => { refs.splice(i, 1); renderRefs(); };
    row.appendChild(del);

    box.appendChild(row);
  });
  if ($('refRow')) $('refRow').style.display = refs.length ? '' : 'none';
  renderSlotPreview();
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/**
 * Full numbering legend. There are TWO independent numbering systems here and
 * conflating them is the bug this whole feature exists to prevent, so both are
 * spelled out side by side:
 *   #N   = batch order of the images to edit (one request per image)
 *   图N  = position inside a SINGLE request (图1 = content, 图2 = red mask
 *          guide, 图3+ = references)
 */
function renderSlotPreview() {
  const el = $('slotPreview');
  if (!el) return;
  const f = engFlags();
  const cur = (active >= 0 && films[active]) ? films[active] : null;
  const out = [];

  out.push('<b>① 批量队列 ·「要改的图」</b>　共 ' + films.length + ' 张，每张单独发一次请求');
  if (films.length) {
    films.forEach((x, i) => {
      out.push('　<span class="k">#' + (i + 1) + '</span>'
        + (i === active ? ' <b>← 当前选中</b>' : '') + '　' + esc(x.name));
    });
  } else {
    out.push('　（未加载图片 → 将以文生图模式运行，没有内容图）');
  }

  out.push('');
  out.push('<b>② 单次请求里的图片编号</b>（会自动写在提示词最前面）');
  slotPlan().forEach(s => {
    let who = '';
    if (s.n === 1) {
      who = cur
        ? '　← 批量 <span class="k">#' + (active + 1) + '</span> ' + esc(cur.name)
        : '　← 文生图，无输入图片';
    }
    out.push('　<span class="k">图' + s.n + '</span> = ' + esc(s.label) + who);
  });

  const max = maxRefsNow();
  if (refs.length && !f.multi) {
    out.push('<b>⚠️ 当前引擎不接受多于 1 张输入图片（HTTP 400）</b>'
      + ' → 请改用 GPT Image 2，或清空参考图。');
  } else if (refs.length > max) {
    out.push('<b>⚠️ 参考图 ' + refs.length + ' 张超出上限</b>（当前引擎与模式下最多 '
      + max + ' 张）：接口只接受 4 张图，内容图'
      + (maskSlotUsed() ? ' + 红色标记图' : '') + '先占位。'
      + '把「修改范围」改成「整张图」，或减少参考图。');
  }
  if (!refs.length) {
    out.push('　（未添加参考图：请求里只有内容图'
      + (maskSlotUsed() ? ' + 红色标记图' : '') + '，与改动前完全一致）');
  }
  el.className = 'hint slotLegend';
  el.innerHTML = out.join('<br>');
}

if ($('refFile')) {
  $('refFile').addEventListener('change', ev => {
    const picked = Array.from(ev.target.files || []).filter(f => /^image\//.test(f.type));
    if (!picked.length) { setMsg('参考图：没有选中图片文件', 'bad'); return; }
    let pending = picked.length;
    const done = () => { ev.target.value = ''; renderRefs(); };
    picked.forEach(f => {
      const im = new Image();
      im.onerror = () => {
        setMsg('参考图解码失败：' + f.name, 'bad');
        if (--pending === 0) done();
      };
      im.onload = () => {
        refs.push({ name: f.name, im, role: 'style' });
        if (--pending === 0) done();
      };
      im.src = URL.createObjectURL(f);
    });
  });
}
if ($('clearRefs')) $('clearRefs').onclick = () => { refs = []; renderRefs(); };


const GROK_SIZES = {
  '1k': [['1024x1024', '1024x1024 方形 1:1']],
  '2k': [['2048x2048', '2048x2048 方形 1:1']],
  '4k': [['2160x3840', '2160x3840 竖幅 9:16'], ['2880x2880', '2880x2880 方形 1:1'], ['3840x2160', '3840x2160 横幅 16:9']],
};

// ---- "follow the source image's aspect ratio" -----------------------------
// The upstream only accepts a FIXED whitelist of sizes (three per quality tier),
// so this can never produce an arbitrary ratio. What it does instead: pick the
// closest LEGAL size for the image actually being generated, and state exactly
// how close that is — plus which other tier would be closer, since the two
// tiers do not share their portrait/landscape ratios at all.
// While it is on, it owns the 尺寸 select (disabled) and decides the size per
// image, so a batch of mixed ratios each gets its own best fit.
function followRatioOn() {
  return !!($('followRatio') && $('followRatio').checked);
}

function engSizeList() {
  const eng = currentEngine();
  if (eng === 'grok') {
    return GROK_SIZES[$('resolution') ? $('resolution').value : '1k'] || GROK_SIZES['1k'];
  }
  return SIZES[$('quality') ? $('quality').value : 'low'] || SIZES.low;
}

/** Closest simple ratio, for a human-readable "≈2:3". */
function fmtAr(ar) {
  const cands = [[9, 16], [2, 3], [3, 4], [1, 1], [4, 3], [3, 2], [16, 9]];
  let best = null;
  cands.forEach(c => {
    const d = Math.abs(c[0] / c[1] - ar);
    if (!best || d < best.d) best = { s: c[0] + ':' + c[1], d };
  });
  return ar.toFixed(3) + (best && best.d < 0.02 ? '（≈' + best.s + '）' : '');
}

function nearestSizeFor(film, list) {
  const ar = film.im.naturalWidth / film.im.naturalHeight;
  let best = null;
  (list || engSizeList()).forEach(entry => {
    const wh = entry[0].split('x');
    const v = Number(wh[0]) / Number(wh[1]);
    const d = Math.abs(v - ar);
    if (!best || d < best.diff) best = { size: entry[0], label: entry[1], ar: v, diff: d };
  });
  return { ar: ar, best: best };
}

/**
 * Set the size for `film` (defaults to the active one) and explain the choice.
 * Called from refreshSizes, renderThumbs and generateOne, so the value always
 * matches the image about to be generated.
 */
function applyFollowRatio(film) {
  const sel = $('size');
  const hint = $('ratioHint');
  const on = followRatioOn();
  if (sel) sel.disabled = on;
  if (!on) { if (hint) hint.textContent = ''; return; }
  if (!sel) return;

  const f = film || ((active >= 0 && films[active]) ? films[active] : null);
  if (!f) {
    if (hint) hint.textContent = '跟随原图比例已开启；加载图片后会自动选尺寸。';
    return;
  }
  const r = nearestSizeFor(f);
  if (!r.best) return;
  sel.value = r.best.size;

  const lines = ['跟随原图：' + esc(f.name) + ' 比例 ' + fmtAr(r.ar)
    + ' → 尺寸 ' + r.best.size + '（' + r.best.label + '）'];
  if (r.best.diff <= 0.02) {
    lines.push('比例误差 ' + r.best.diff.toFixed(3) + '，基本吻合，不会被补白或裁切。');
  } else {
    lines.push('比例误差 ' + r.best.diff.toFixed(3) + '，比原图'
      + (r.best.ar < r.ar ? '更瘦长' : '更矮胖')
      + ' → 会按「适配」的设置补白边或裁切。');
    // the tiers do not share their ratios, so a different tier can fit better
    const tiers = (currentEngine() === 'grok') ? GROK_SIZES : SIZES;
    let sug = null;
    Object.keys(tiers).forEach(t => {
      (tiers[t] || []).forEach(entry => {
        const wh = entry[0].split('x');
        const d = Math.abs(Number(wh[0]) / Number(wh[1]) - r.ar);
        if (d < r.best.diff - 1e-9 && (!sug || d < sug.diff)) {
          sug = { tier: t, size: entry[0], diff: d };
        }
      });
    });
    if (sug) {
      lines.push('换「' + sug.tier + '」档可得 ' + sug.size
        + '（误差 ' + sug.diff.toFixed(3) + '），更接近原图。');
    } else {
      lines.push('当前引擎没有更接近的比例可选。');
    }
  }
  if (hint) hint.textContent = lines.join('\n');
}

function refreshSizes() {
  const eng = currentEngine();
  let list;
  if (eng === 'grok') {
    list = GROK_SIZES[$('resolution') ? $('resolution').value : '1k'] || GROK_SIZES['1k'];
  } else {
    list = SIZES[$('quality') ? $('quality').value : 'low'] || SIZES.low;
  }
  const sel = $('size');
  sel.innerHTML = '';
  list.forEach(([v, label]) => {
    const o = document.createElement('option'); o.value = v; o.textContent = label;
    sel.appendChild(o);
  });
  const idx = list.findIndex(p => p[0] === savedSize);
  sel.selectedIndex = idx >= 0 ? idx : 0;
  if (!followRatioOn()) {
    // persist only a MANUAL choice: while following, the auto-picked value must
    // not overwrite what the user chose before enabling the checkbox
    savedSize = sel.value;
    store.set('mie_size', sel.value);
  }
  $('sizeHint').textContent = eng === 'grok'
    ? 'Grok：档位由 resolution 决定，size 仅用于计费；上游官方目前列出 1k / 2k，4k 可能被拒。'
    : '画质决定档位，尺寸必须属于同一档：low=1K / medium=2K / high=4K。跨档组合会被接口拒绝。';
  applyFollowRatio();
}

function applyEngine() {
  const eng = currentEngine();
  const d = ENGINE_DEFAULTS[eng] || ENGINE_DEFAULTS.gpt;
  $('apiKey').value = d.key;
  if ($('model')) $('model').value = d.model;
  if ($('engineHint')) $('engineHint').textContent = d.hint;

  const wantQuality = d.kind === 'quality';
  if ($('qualityRow')) $('qualityRow').style.display = wantQuality ? '' : 'none';
  if ($('resolutionRow')) $('resolutionRow').style.display = wantQuality ? 'none' : '';
  if ($('quality') && !wantQuality) $('quality').value = 'low';

  const scopeSel = $('scope');
  const maskOpt = scopeSel.querySelector('option[value="mask"]');
  if (!wantQuality) {
    if (scopeSel.value === 'mask') scopeSel.value = 'whole';
    if (maskOpt) { maskOpt.disabled = true; maskOpt.textContent = '仅涂过的区域（Grok 不支持）'; }
  } else if (maskOpt) {
    maskOpt.disabled = false; maskOpt.textContent = '仅涂过的区域（需要涂遮罩）';
  }
  refreshSizes();
  updateScopeHint();
  // re-render the reference rows, not just the legend: their 图N badges depend
  // on the engine (mask support) and would otherwise go stale and mislead.
  if (typeof renderRefs === 'function') renderRefs();
}

$('quality').addEventListener('change', refreshSizes);
if ($('resolution')) $('resolution').addEventListener('change', refreshSizes);
if ($('engine')) {
  $('engine').addEventListener('change', () => { store.set('mie_engine', currentEngine()); applyEngine(); });
}
$('size').addEventListener('change', () => { savedSize = $('size').value; store.set('mie_size', savedSize); });

// follow-ratio toggle. Restored BEFORE the start-up refreshSizes() below, so the
// very first render already reflects the saved state.
if ($('followRatio')) {
  $('followRatio').checked = store.get('mie_follow_ratio') === '1';
  $('followRatio').addEventListener('change', () => {
    store.set('mie_follow_ratio', $('followRatio').checked ? '1' : '0');
    applyFollowRatio();
  });
}

const base = () => $('baseUrl').value.trim().replace(/\/+$/, '');
const key  = () => $('apiKey').value.trim();

// ---- persisted settings: HTML defaults win when nothing is saved yet ----
const DEFAULTS = {
  baseUrl: 'https://image-direct.geiliapi.com/v1',
  apiKey: 'sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915',
  model: 'gpt-image-2',
  prompt: '替换背景为无任何可辨认物体的平滑灰绿渐变：低饱和灰绿与灰橄榄色，左亮右暗的柔和明暗过渡，四角略暗，过渡处没有可见分界线。背景干净无纹理：不要纸张颗粒、不要水渍斑点、不要云絮雾状、不要涂抹笔触、不要建筑、墙面、地面、树木或任何地标。',
};
for (const [id, dv] of Object.entries(DEFAULTS)) {
  const saved = store.get('mie_' + id);
  $(id).value = saved !== null && saved !== '' ? saved : dv;
  $(id).addEventListener('input', () => store.set('mie_' + id, $(id).value));
  $(id).addEventListener('change', () => store.set('mie_' + id, $(id).value));
}
for (const id of ['quality','fitMode','maskMode','scope','engine','resolution']) {
  const v = store.get('mie_' + id);
  if (v !== null && $(id)) $(id).value = v;
  if ($(id)) $(id).addEventListener('change', () => store.set('mie_' + id, $(id).value));
}
// NOTE: updateScopeHint() is deliberately NOT called here. It depends on
// wholeMode(), a `const` declared further down, and calling it this early threw
// "Cannot access 'wholeMode' before initialization" (TDZ) which aborted the
// whole script. applyEngine() (which calls it) runs next to its definition.
refreshSizes();
$('eye').onclick = () => {
  const el = $('apiKey');
  el.type = el.type === 'password' ? 'text' : 'password';
};
function resetConn() {
  for (const [id, dv] of Object.entries(DEFAULTS)) {
    store.del('mie_' + id); $(id).value = dv;
  }
}
window.resetConn = resetConn;
refreshSizes();

// ---- mask layer: white = paint = allow changes ----
const mc = document.createElement('canvas');
const mctx = mc.getContext('2d');

function setMsg(text, kind) {
  const m = $('msg');
  m.className = 'msg' + (kind ? ' ' + kind : '');
  m.textContent = text || '';
  if (!text) m.className = 'msg';
}

function fitCanvas(im) {
  const w = Math.min(im.naturalWidth, 900);
  scale = w / im.naturalWidth;
  cv.width = Math.round(im.naturalWidth * scale);
  cv.height = Math.round(im.naturalHeight * scale);
}

// load a list of files (1..n). The first becomes active; the rest queue up.
function loadFiles(list) {
  const arr = Array.from(list || []).filter(f => /^image\//.test(f.type));
  const bad = Array.from(list || []).filter(f => !/^image\//.test(f.type));
  if (bad.length) setMsg('跳过非图片文件：' + bad.map(f => f.name).join(', '), 'bad');
  if (!arr.length) { if (!bad.length) setMsg('没有选中文件', 'bad'); return; }

  let pending = arr.length;
  arr.forEach((f, idx) => {
    const im = new Image();
    im.onerror = () => { setMsg('图片解码失败：' + f.name, 'bad'); if (--pending === 0) finishLoad(); };
    im.onload = () => {
      const mc = document.createElement('canvas');
      fitCanvas(im);
      mc.width = cv.width; mc.height = cv.height;
      films.push({ name: f.name, im, mc, masked: false, resultB64: null });
      if (--pending === 0) finishLoad(idx === 0);
    };
    im.src = URL.createObjectURL(f);
  });
}

function finishLoad() {
  const n = films.length;
  $('fileName').textContent = n > 1
    ? `已载入 ${n} 张图片`
    : '已选择：' + films[0].name;
  $('editor').style.display = '';
  $('batchRow').style.display = '';
  $('runAll').disabled = n < 2;
  // keep the user's current image selected when appending; only auto-pick when
  // nothing was active yet
  if (active < 0 || active >= n) selectFilm(n - 1, true);
  else { saveActiveMask(); renderThumbs(); }
  renderThumbs();
}

function renderThumbs() {
  const box = $('thumbs');
  box.innerHTML = '';
  films.forEach((f, i) => {
    const d = document.createElement('div');
    d.className = 'th' + (i === active ? ' on' : '') + (f.masked ? ' masked' : '');
    // batch order, always starting at #1 — NOT the same thing as the request
    // slot number (图1 is whatever batch item is being processed right now).
    d.title = `批量第 ${i + 1} 张：${f.name}`
      + (i === active ? '（当前选中，生成时作为「图1 = 内容图」）' : '')
      + (f.masked ? '　已涂遮罩' : '');
    const t = document.createElement('img');
    t.src = f.im.src;
    d.appendChild(t);

    const num = document.createElement('span');
    num.className = 'num';
    num.textContent = '#' + (i + 1);
    d.appendChild(num);

    const dot = document.createElement('span'); dot.className = 'dot';
    d.appendChild(dot);
    d.onclick = () => selectFilm(i);
    box.appendChild(d);
  });
  const nMasked = films.filter(f => f.masked).length;
  $('batchInfo').textContent = `${films.length} 张，其中 ${nMasked} 张已涂遮罩`
    + (films.length > 1 ? '（批量：每张单独发一次请求）' : '');
  $('imgInfo').textContent = img ? `${img.naturalWidth}×${img.naturalHeight}` : '未加载图片';
  applyFollowRatio();   // the followed size depends on which image is selected
  renderSlotPreview();
}

// save the on-screen canvas back into the film that is currently active
function saveActiveMask() {
  if (active < 0 || !films[active]) return;
  const f = films[active];
  f.mc.width = mc.width; f.mc.height = mc.height;
  const c = f.mc.getContext('2d');
  c.clearRect(0, 0, f.mc.width, f.mc.height);
  c.drawImage(mc, 0, 0);
  f.masked = maskHasContent(mc);
}

// count painted pixels in a mask canvas
function maskPixels(canvas) {
  if (!canvas || !canvas.width) return 0;
  const d = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
  let n = 0;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 127) n++;
  return n;
}
const MASK_MIN_PX = 8;   // a deliberate click should already count as a mask
function maskHasContent(canvas) { return maskPixels(canvas) >= MASK_MIN_PX; }

function selectFilm(i, keepZoom) {
  if (active === i) return;
  saveActiveMask();
  active = i;
  const f = films[i];
  img = f.im;
  if (!keepZoom) {
    const w = Math.min(f.im.naturalWidth, 900);
    scale = w / f.im.naturalWidth;
    cv.width = Math.round(f.im.naturalWidth * scale);
    cv.height = Math.round(f.im.naturalHeight * scale);
  }
  mc.width = cv.width; mc.height = cv.height;
  mctx.clearRect(0, 0, mc.width, mc.height);
  if (f.mc.width) mctx.drawImage(f.mc, 0, 0, mc.width, mc.height);
  hasMask = maskHasContent(mc);
  redraw(); updateMaskStat(); renderThumbs();
  $('run').disabled = false;
  // restore a previous result for this image, if any
  if (f.resultB64) showResult(f.resultB64, f.name);
  else { $('outBox').className = 'hint'; $('outBox').textContent = '尚未生成'; $('download').disabled = true; resultURL = null; }
}

function showResult(b64, name) {
  resultURL = 'data:image/png;base64,' + b64;
  $('outBox').className = '';
  $('outBox').innerHTML = '';
  const cap = document.createElement('div');
  cap.className = 'hint'; cap.textContent = name || '';
  const el = document.createElement('img'); el.className = 'out'; el.src = resultURL;
  $('outBox').appendChild(cap); $('outBox').appendChild(el);
  $('download').disabled = false;
}

function loadFile(f) {
  if (!f) return;
  if (!/^image\//.test(f.type)) {
    setMsg('这个文件不是图片：' + f.name + '（type=' + (f.type || '未知') + '）', 'bad');
    return;
  }
  const url = URL.createObjectURL(f);
  const im = new Image();
  im.onerror = () => setMsg('图片解码失败：' + f.name, 'bad');
  im.onload = () => {
    img = im;
    const w = Math.min(im.naturalWidth, 900);
    scale = w / im.naturalWidth;
    cv.width = Math.round(im.naturalWidth * scale);
    cv.height = Math.round(im.naturalHeight * scale);
    mc.width = cv.width; mc.height = cv.height;
    mctx.clearRect(0, 0, mc.width, mc.height);
    hasMask = false;
    redraw();
    $('editor').style.display = '';
    $('drop').style.display = 'none';
    $('imgInfo').textContent = `${im.naturalWidth}×${im.naturalHeight}`;
    $('run').disabled = false;
    updateMaskStat();
  };
  im.src = url;
}

function redraw() {
  if (!img) return;
  // two-pass composite: white mask -> red, then overlay at low alpha
  const tint = document.createElement('canvas');
  tint.width = mc.width; tint.height = mc.height;
  const tc = tint.getContext('2d');
  tc.drawImage(mc, 0, 0);
  tc.globalCompositeOperation = 'source-in';     // keep only painted pixels
  tc.fillStyle = 'rgba(255,40,40,1)';
  tc.fillRect(0, 0, tint.width, tint.height);

  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  ctx.globalAlpha = 0.45;
  ctx.drawImage(tint, 0, 0, cv.width, cv.height);
  ctx.globalAlpha = 1;
}

function pos(e) {
  const r = cv.getBoundingClientRect();
  const t = e.touches ? e.touches[0] : e;
  return { x: (t.clientX - r.left) * cv.width / r.width,
           y: (t.clientY - r.top) * cv.height / r.height };
}

function stroke(a, b) {
  // Brush size is given in DISPLAY pixels (what the user sees on the slider).
  // Canvas coords are in internal pixels, so the conversion factor is
  // (canvas.width / displayed width) - it must be MULTIPLIED. The previous
  // version divided, which shrank the brush to a few pixels and made valid
  // strokes register as an empty mask.
  const rect = cv.getBoundingClientRect();
  const factor = rect.width > 0 ? cv.width / rect.width : 1;
  const r = Math.max(2, parseInt($('brush').value, 10) * factor);
  mctx.globalCompositeOperation = 'source-over';
  mctx.strokeStyle = erase ? 'rgba(0,0,0,0)' : '#ffffff';
  mctx.fillStyle = erase ? 'rgba(0,0,0,0)' : '#ffffff';
  mctx.lineWidth = r; mctx.lineCap = 'round'; mctx.lineJoin = 'round';
  if (erase) mctx.globalCompositeOperation = 'destination-out';
  mctx.beginPath(); mctx.moveTo(a.x, a.y); mctx.lineTo(b.x, b.y); mctx.stroke();
  mctx.beginPath(); mctx.arc(b.x, b.y, r / 2, 0, Math.PI * 2); mctx.fill();
  mctx.globalCompositeOperation = 'source-over';
  hasMask = true;
}

let last = null;
cv.addEventListener('pointerdown', e => {
  if (!img) return; drawing = true; last = pos(e);
  stroke(last, last); redraw(); cv.setPointerCapture(e.pointerId);
});
cv.addEventListener('pointermove', e => {
  if (!drawing) return;
  const p = pos(e); stroke(last, p); last = p; redraw();
});
cv.addEventListener('pointerup', e => {
  drawing = false; updateMaskStat(); renderThumbs();
  try { cv.releasePointerCapture(e.pointerId); } catch (_) {}
});

function updateMaskStat() {
  if (!mc.width) return;
  const d = mctx.getImageData(0, 0, mc.width, mc.height).data;
  let n = 0;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 127) n++;
  const pct = (n / (mc.width * mc.height) * 100);
  // authoritative state: derived from the pixels, never from a flag
  hasMask = n >= MASK_MIN_PX;
  $('maskStat').textContent = n > 0
    ? `遮罩覆盖率 ${pct.toFixed(2)}%（${n.toLocaleString()} 像素）`
    : '遮罩覆盖率 0%　未涂';
  $('maskStat').style.color = n > 0 ? 'var(--ok)' : 'var(--dim)';
  if (active >= 0 && films[active]) films[active].masked = hasMask;
}
function updateBrush() {
  const rect = cv.getBoundingClientRect();
  const factor = rect.width > 0 ? cv.width / rect.width : 1;
  const canvasR = Math.round(parseInt($('brush').value, 10) * factor);
  $('brushVal').textContent = $('brush').value + '（画布 ' + canvasR + 'px）';
}
$('brush').addEventListener('input', updateBrush); updateBrush();
window.addEventListener('resize', updateBrush);

// Belt and braces: the <label for="file"> opens the picker natively (no JS
// needed), the visible <input> works on its own, and this handler covers the
// case where the user clicks the dashed box itself.
$('drop').addEventListener('click', e => {
  e.preventDefault(); e.stopPropagation();
  $('file').click();
});
$('file').onchange = e => {
  const files = e.target.files;
  if (files && files.length) {
    // APPEND, never replace: picking one file at a time must build up a batch.
    // (The `multiple` attribute is present, but some sandboxed/embedded
    // browsers ignore it and only ever hand back one file.)
    $('fileName').textContent = `正在载入 ${files.length} 个文件…`;
    loadFiles(files);
  }
  e.target.value = '';                  // allow re-picking the same file
};
$('addMore').onclick = () => $('file').click();
$('clearList').onclick = () => {
  if (!films.length) return;
  if (!confirm('清空已载入的图片列表？未生成的结果会丢失。')) return;
  films = []; active = -1; img = null; hasMask = false;
  $('thumbs').innerHTML = '';
  $('editor').style.display = 'none';
  $('fileName').textContent = '已清空，请重新选择图片';
  $('run').disabled = true; $('runAll').disabled = true;
  $('outBox').className = 'hint'; $('outBox').textContent = '尚未生成';
  $('download').disabled = true; resultURL = null;
  $('imgInfo').textContent = '未加载图片';
  $('maskStat').textContent = '遮罩覆盖率 0%';
};
$('drop').addEventListener('dragover', e => { e.preventDefault(); $('drop').classList.add('over'); });
$('drop').addEventListener('dragleave', () => $('drop').classList.remove('over'));
$('drop').addEventListener('drop', e => {
  e.preventDefault(); $('drop').classList.remove('over');
  const files = e.dataTransfer.files;
  if (files && files.length) {
    $('fileName').textContent = `正在载入 ${files.length} 个文件…`;
    loadFiles(files);                      // append, same as the picker
  }
});
$('erase').onclick = () => { erase = !erase; $('erase').textContent = erase ? '画笔模式' : '橡皮模式'; };
$('clear').onclick = () => {
  mctx.clearRect(0, 0, mc.width, mc.height); hasMask = false;
  saveActiveMask(); redraw(); updateMaskStat(); renderThumbs();
};
$('invert').onclick = () => {
  if (!mc.width) return;
  const d = mctx.getImageData(0, 0, mc.width, mc.height);
  for (let i = 0; i < d.data.length; i += 4) {
    const on = d.data[i + 3] > 127;
    d.data[i] = 255; d.data[i + 1] = 255; d.data[i + 2] = 255;
    d.data[i + 3] = on ? 0 : 255;
  }
  mctx.putImageData(d, 0, 0); hasMask = true;
  saveActiveMask(); redraw(); updateMaskStat(); renderThumbs();
};
$('fit').onclick = () => { if (img) loadFileFromImg(); };
function loadFileFromImg() {
  const w = Math.min(img.naturalWidth, 900);
  const s = w / img.naturalWidth;
  const old = document.createElement('canvas');
  old.width = mc.width; old.height = mc.height;
  old.getContext('2d').drawImage(mc, 0, 0);
  cv.width = Math.round(img.naturalWidth * s); cv.height = Math.round(img.naturalHeight * s);
  mc.width = cv.width; mc.height = cv.height;
  mctx.drawImage(old, 0, 0, mc.width, mc.height);
  redraw(); updateMaskStat();
}

// ---- API helpers ----
async function testConn() {
  setMsg('测试中…');
  try {
    const r = await fetch(api('/api/ping'), {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ base_url: base(), api_key: key() })
    });
    const j = await r.json();
    setMsg(j.message, j.ok ? 'ok' : 'bad');
  } catch (e) { setMsg('本地服务异常: ' + e.message, 'bad'); }
}
$('test').onclick = testConn;

$('listModels').onclick = async () => {
  setMsg('获取模型列表…');
  try {
    const r = await fetch(api('/api/models'), {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ base_url: base(), api_key: key() })
    });
    const j = await r.json();
    if (!j.ok) { setMsg(j.message, 'bad'); return; }
    const dl = $('models'); dl.innerHTML = '';
    j.models.forEach(m => { const o = document.createElement('option'); o.value = m; dl.appendChild(o); });
    setMsg(`拿到 ${j.models.length} 个模型。含 image 关键字的：\n` +
           (j.image_models.length ? j.image_models.join('\n') : '（无）'), 'ok');
  } catch (e) { setMsg('本地服务异常: ' + e.message, 'bad'); }
};

function blobOf(canvas) {
  return new Promise(res => canvas.toBlob(res, 'image/png'));
}

// convert any loaded image into a Blob suitable for upload.
// Re-encodes at a bounded size: the API target is at most 1536 px on the long
// side, so sending a 20 MP original just burns upload time and can exceed the
// multipart limits. PNG for line art, JPEG when it is large, to stay small.
const MAX_EDGE = 1600;
const MAX_BYTES = 4 * 1024 * 1024;
function imageBlob(film) {
  return new Promise(res => {
    const im = film.im;
    const s = Math.min(1, MAX_EDGE / Math.max(im.naturalWidth, im.naturalHeight));
    const w = Math.max(1, Math.round(im.naturalWidth * s));
    const h = Math.max(1, Math.round(im.naturalHeight * s));
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const g = c.getContext('2d');
    g.fillStyle = '#ffffff'; g.fillRect(0, 0, w, h);   // flatten any alpha
    g.drawImage(im, 0, 0, w, h);

    c.toBlob(png => {
      if (png && png.size <= MAX_BYTES) {
        res({ blob: png, ext: 'png', size: png.size, w, h });
        return;
      }
      c.toBlob(jpg => {
        const b = jpg || png;
        res({ blob: b, ext: 'jpg', size: b ? b.size : 0, w, h });
      }, 'image/jpeg', 0.92);
    }, 'image/png');
  });
}

async function callEdit(film) {
  const eng = (typeof $('engine') !== 'undefined' && $('engine')) ? $('engine').value : 'gpt';
  const whole = $('scope').value === 'whole';
  // no image selected -> text-to-image; otherwise image-to-image
  const operation = film ? 'i2i' : 't2i';

  const fd = new FormData();
  fd.append('engine', eng);
  fd.append('operation', operation);
  fd.append('base_url', base());
  fd.append('api_key', key());
  fd.append('model', $('model').value.trim());
  fd.append('prompt', $('prompt').value);
  fd.append('size', $('size').value);
  fd.append('quality', $('quality') ? $('quality').value : 'low');
  fd.append('resolution', $('resolution') ? $('resolution').value : '1k');
  fd.append('pad_mode', $('fitMode').value);
  fd.append('mask_mode', $('maskMode').value);
  fd.append('scope', $('scope').value);

  // reference images — attached to THIS request (not queued as jobs).
  // Names must be distinct parts: parse_multipart keys files by field name, so
  // repeated "ref_file" would silently collapse to the last one.
  fd.append('ref_count', String(refs.length));
  fd.append('ref_roles', JSON.stringify(refs.map(r => r.role)));
  for (let i = 0; i < refs.length; i++) {
    const rinfo = await imageBlob({ im: refs[i].im });
    fd.append('ref_file_' + i, rinfo.blob,
              'ref' + (i + 1) + '_' + refs[i].role + '.' + rinfo.ext);
  }
  diag.refs = refs.length
    ? refs.map((r, i) => `图${i + (maskSlotUsed() ? 3 : 2)}=${r.role}(${r.name})`).join(' ')
    : '（无）';

  let maskInfo = '（文生图，无输入图片）';
  if (film) {
    const info = await imageBlob(film);
    fd.append('image_file', info.blob, 'image.' + info.ext);
    diag.image = `${info.w}x${info.h} ${info.ext} ${(info.size / 1024).toFixed(0)} KB`;
    maskInfo = '（整张图模式，无遮罩）';
    if (!whole) {
      const mb = await blobOf(film.mc);
      fd.append('mask_file', mb, 'mask.png');
      maskInfo = `mask.png ${(mb.size / 1024).toFixed(0)} KB`;
    }
  } else {
    diag.image = '（无）';
  }
  diag.mask = maskInfo;
  diag.engine = eng;

  const t0 = Date.now();
  const ctl = new AbortController();
  const TO = 15 * 60 * 1000;               // 15 min hard ceiling
  const tid = setTimeout(() => ctl.abort(), TO);
  let resp, text;
  try {
    resp = await fetch(api('/api/edit'), { method: 'POST', body: fd, signal: ctl.signal });
    text = await resp.text();
  } catch (e) {
    clearTimeout(tid);
    return { ok: false, message: e.name === 'AbortError'
      ? `请求超时（超过 ${TO / 60000} 分钟）\n本地服务地址：${api('/api/edit')}`
      : `网络请求失败：${e.name}: ${e.message}\n本地服务地址：${api('/api/edit')}` };
  }
  clearTimeout(tid);
  diag.ms = Date.now() - t0;

  if (!resp.ok) {
    return { ok: false, message: `本地服务返回 HTTP ${resp.status}\n${String(text).slice(0, 600)}` };
  }
  try {
    return JSON.parse(text);
  } catch (e) {
    return { ok: false, message: `返回内容不是 JSON（前 600 字符）：\n${String(text).slice(0, 600)}` };
  }
}

const wholeMode = () => $('scope').value === 'whole';

function updateScopeHint() {
  const w = wholeMode();
  // whole mode is the default: hide the paint tools entirely so nothing implies
  // that masking is required
  $('maskStat').style.display = w ? 'none' : '';
  $('maskTools').style.display = w ? 'none' : '';
  $('scopeHint').textContent = w
    ? '整张图直接交给模型重绘，不需要涂任何东西。'
    : '切换到左边画布——画笔工具会出现在画布下方，按住左键拖动涂出要修改的地方。';
}
$('scope').addEventListener('change', () => {
  store.set('mie_scope', $('scope').value);
  updateScopeHint();
  // the red mask guide takes image[1] in mask mode, so every reference's 图N
  // badge shifts by one — re-render the rows, not only the legend.
  renderRefs();
});
updateScopeHint();
// Draw the numbering legend once at start-up, so the two numbering systems are
// visible before anything is uploaded. This call site is deliberately below
// every declaration it depends on — check_tdz.py guards against regressions.
renderSlotPreview();

function preflight() {
  if (!films.length) { setMsg('请先选择图片', 'bad'); return false; }
  if (!base() || !key()) { setMsg('请先填 Base URL 和 API Key', 'bad'); return false; }
  if (!$('prompt').value.trim()) { setMsg('请填写提示词', 'bad'); return false; }
  // reference-image guards, checked here so the user sees the reason before any
  // request is spent. The server enforces the same rules again.
  if (refs.length) {
    const f = engFlags();
    if (!f.multi) {
      setMsg('当前引擎「' + (ENGINE_DEFAULTS[currentEngine()] || {}).model + '」不接受多于 1 张输入图片'
        + '（上游 HTTP 400）。\n你已添加 ' + refs.length + ' 张参考图。\n\n'
        + '请改用「GPT Image 2」引擎，或清空参考图列表。', 'bad');
      return false;
    }
    const max = maxRefsNow();
    if (refs.length > max) {
      const maskSlot = engFlags().mask && !wholeModeNow();
      setMsg('参考图数量超出上限：当前模式下最多 ' + max + ' 张。\n\n'
        + '原因：接口只接受 4 张图（image / image[1] / image[2] / image[3]），'
        + '本请求固定占用 1 张内容图'
        + (maskSlot ? ' + 1 张红色标记图' : '') + '，剩下的位置才是参考图。\n\n'
        + (maskSlot ? '二选一：把「修改范围」改成「整张图」腾出位置，或减少参考图。'
                    : '请减少参考图。'), 'bad');
      return false;
    }
  }
  return true;
}

// shared cores used by both the single and the batch buttons
async function generateOne(i, tag) {
  const f = films[i];
  if (!wholeMode() && !maskHasContent(f.mc)) {
    return { i, ok: false, message: f.name + '：未涂遮罩' };
  }
  // resolve the size for THIS image first: with 跟随原图比例 on, a batch of
  // mixed aspect ratios must each generate at their own best-fit size.
  applyFollowRatio(f);
  const j = await callEdit(f);
  if (j.ok) { f.resultB64 = j.image_b64; f.masked = true; }
  else if (!j.message && !j.raw) { j.message = '服务端未返回错误说明，原始响应为空'; }
  return { i, ok: j.ok, message: j.message, name: f.name,
           slotMap: j.slot_map, partsSent: j.parts_sent,
           size: ($('size') ? $('size').value : '') };
}

/** One-line echo of what the server confirms it actually sent. */
function sentLine(r) {
  if (!r || !r.ok) return '';
  const sz = r.size ? `\n尺寸：${r.size}` + (followRatioOn() ? '（跟随原图自动选定）' : '') : '';
  if (Array.isArray(r.slotMap) && r.slotMap.length) {
    const plan = r.slotMap.map(s => '图' + s.index + '=' + s.label).join(' | ');
    const parts = Array.isArray(r.partsSent) ? r.partsSent.join(' + ') : '';
    return sz + `\n已发送的图片：${plan}` + (parts ? `\n实际 parts：${parts}` : '');
  }
  return sz + (Array.isArray(r.partsSent) ? `\n实际 parts：${r.partsSent.join(' + ')}` : '');
}

let busy = false;
function setBusy(v) {
  busy = v;
  $('run').disabled = v;
  $('runAll').disabled = v || films.length < 2;
}

$('run').onclick = async () => {
  if (busy) return;
  if (!base() || !key()) { setMsg('请先填 Base URL 和 API Key', 'bad'); return; }
  if (!$('prompt').value.trim()) { setMsg('请填写提示词', 'bad'); return; }

  const film = (active >= 0 && films[active]) ? films[active] : null;
  if (!film) {
    // no image loaded -> text-to-image
    setBusy(true);
    const t0 = Date.now();
    try {
      setMsg('文生图中…（已等待 0s）');
      const timer = setInterval(() => {
        if (busy) setMsg(`文生图中…（已等待 ${Math.round((Date.now() - t0) / 1000)}s）`);
      }, 1000);
      const j = await callEdit(null);
      clearInterval(timer);
      if (j.ok) {
        showResult(j.image_b64, '文生图结果');
        setMsg(`文生图完成，用时 ${Math.round((Date.now() - t0) / 1000)}s`, 'ok');
      } else {
        setMsg('文生图失败：\n' + (j.message || '未知错误') + '\n\n—— 诊断信息 ——\n' + diagText(), 'bad');
      }
    } catch (e) {
      setMsg('异常：' + e.message, 'bad');
    } finally { setBusy(false); }
    return;
  }

  saveActiveMask();
  const i = active;
  if (!wholeMode()) {
    const px = maskPixels(film.mc);
    if (px < MASK_MIN_PX) {
      setMsg(`画布上没有检测到涂改区域（当前 ${px} 像素）。\n\n`
        + `两种解决办法：\n`
        + `1) 在画布上【按住鼠标左键拖动】涂出要修改的地方（不是单击）；`
        + `涂的过程中左上角会显示「遮罩覆盖率」，数字变大就说明涂上了。\n`
        + `2) 不想指定范围，就把「修改范围」改成「整张图（无需涂遮罩）」，`
        + `然后直接点生成。\n\n`
        + `如果已经涂了、覆盖率却一直是 0%，请把左上角显示的数字告诉我。`, 'bad');
      return;
    }
  }
  setBusy(true);
  const t0 = Date.now();
  try {
    setMsg('生成中…（已等待 0s）');
    const timer = setInterval(() => {
      if (busy) setMsg(`生成中…（已等待 ${Math.round((Date.now() - t0) / 1000)}s）`);
    }, 1000);
    const r = await generateOne(i);
    clearInterval(timer);
    if (r.ok) {
      showResult(films[i].resultB64, films[i].name);
      setMsg(`完成，用时 ${Math.round((Date.now() - t0) / 1000)}s` + sentLine(r), 'ok');
    } else {
      setMsg('生成失败：\n' + (r.message || '未知错误') + '\n\n—— 诊断信息 ——\n' + diagText(), 'bad');
    }
    renderThumbs();
  } catch (e) {
    setMsg('异常：' + e.message, 'bad');
  } finally { setBusy(false); }
};

$('runAll').onclick = async () => {
  if (busy || !preflight()) return;
  const todo = films.map((f, i) => i)
    .filter(i => wholeMode() || maskHasContent(films[i].mc));
  if (!todo.length) {
    setMsg('没有可生成的图片。整体模式下所有图片都可生成；遮罩模式下请先涂遮罩。', 'bad');
    return;
  }
  const what = wholeMode() ? '整张图重绘' : '按遮罩局部修改';
  if (!confirm(`将对 ${todo.length} 张图依次生成（${what}，共用同一提示词与参数）。继续？`)) return;

  setBusy(true);
  const t0 = Date.now();
  const results = [];
  try {
    for (let k = 0; k < todo.length; k++) {
      const i = todo[k];
      setMsg(`批量生成中… ${k + 1}/${todo.length}　批量 #${i + 1}：${films[i].name}\n`
             + `尺寸 ${$('size').value}${followRatioOn() ? '（跟随原图自动选定）' : ''}`
             + `　已用时 ${Math.round((Date.now() - t0) / 1000)}s`);
      const r = await generateOne(i);
      results.push(r);
      if (r.ok) { films[i].resultB64 = films[i].resultB64; }
      selectFilmSilent(i);
      renderThumbs();
    }
    const okN = results.filter(r => r.ok).length;
    if (!okN) {
      setMsg('批量生成全部失败。\n' + results.map(r => (r.name || '') + '：' + (r.message || '')).join('\n')
             + '\n\n—— 诊断信息 ——\n' + diagText(), 'bad');
    }
    // show every result in the output panel
    $('outBox').className = '';
    $('outBox').innerHTML = '';
    results.forEach(r => {
      if (r.ok) {
        const cap = document.createElement('div'); cap.className = 'hint'; cap.textContent = r.name;
        const el = document.createElement('img'); el.className = 'out';
        el.src = 'data:image/png;base64,' + films[r.i].resultB64;
        $('outBox').appendChild(cap); $('outBox').appendChild(el);
      }
    });
    if (okN) { resultURL = 'data:image/png;base64,' + films[results.find(r => r.ok).i].resultB64; $('download').disabled = false; }
    setMsg(`批量完成：成功 ${okN} / ${results.length}，用时 ${Math.round((Date.now() - t0) / 1000)}s\n`
           + results.map(r => (r.ok ? 'OK   ' : 'FAIL ') + (r.name || '') + (r.ok ? '' : '  ' + (r.message || ''))).join('\n')
           + (results.find(r => r.ok) ? sentLine(results.find(r => r.ok)) : ''),
           okN === results.length ? 'ok' : 'bad');
  } catch (e) {
    setMsg('异常：' + e.message, 'bad');
  } finally { setBusy(false); }
};

$('copyMask').onclick = () => {
  if (active < 0) return;
  saveActiveMask();
  const src = films[active].mc;
  films.forEach((f, i) => {
    if (i === active) return;
    f.mc.width = src.width; f.mc.height = src.height;
    const c = f.mc.getContext('2d');
    c.clearRect(0, 0, f.mc.width, f.mc.height);
    c.drawImage(src, 0, 0);
    f.masked = true;
  });
  renderThumbs();
  setMsg(`已把第 ${active + 1} 张的遮罩复制到其余 ${films.length - 1} 张。`, 'ok');
};

// switch film without re-rendering thumbs (used inside the batch loop)
function selectFilmSilent(i) {
  saveActiveMask();
  active = i;
  const f = films[i];
  img = f.im;
  const w = Math.min(f.im.naturalWidth, 900);
  scale = w / f.im.naturalWidth;
  cv.width = Math.round(f.im.naturalWidth * scale);
  cv.height = Math.round(f.im.naturalHeight * scale);
  mc.width = cv.width; mc.height = cv.height;
  mctx.clearRect(0, 0, mc.width, mc.height);
  if (f.mc.width) mctx.drawImage(f.mc, 0, 0, mc.width, mc.height);
  hasMask = maskHasContent(mc);
  redraw(); updateMaskStat();
}

$('download').onclick = () => {
  if (!resultURL) return;
  const a = document.createElement('a');
  const nm = (active >= 0 && films[active] ? films[active].name.replace(/\.[^.]+$/, '') : 'result');
  a.href = resultURL; a.download = nm + '_edited.png'; a.click();
};
