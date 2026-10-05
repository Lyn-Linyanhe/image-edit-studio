/* Headless harness: run the app's real page script in Node with a minimal DOM
 * stub, then simulate the exact user flow that was failing:
 *   pick one image -> pick another -> assert the queue GREW (append, not replace)
 * Also simulates painting on the canvas and checks the mask is detected.
 *
 * Run: node test_ui.js
 */
const fs = require('fs');
const vm = require('vm');

const js = fs.readFileSync('_page_extracted.js', 'utf8');

// ---------------------------------------------------------------- DOM stub
class Ctx {
  constructor(canvas) {
    this.canvas = canvas;
    this.globalAlpha = 1;
    this.globalCompositeOperation = 'source-over';
    this._px = new Uint8ClampedArray(canvas.width * canvas.height * 4);
  }
  _reset() { this._px = new Uint8ClampedArray(this.canvas.width * this.canvas.height * 4); }
  set fillStyle(v) { this._fill = v; } get fillStyle() { return this._fill; }
  set strokeStyle(v) { this._stroke = v; } get strokeStyle() { return this._stroke; }
  save() {} restore() {} beginPath() {} moveTo() {} lineTo() {} arc() {}
  closePath() {} clearRect() { this._px.fill(0); } fillRect() {} strokeRect() {}
  fillText() {} measureText() { return { width: 10 }; }
  stroke() { this._paint(); }
  fill() { this._paint(); }
  _paint() {
    // approximate: mark the whole plane as painted so mask detection triggers
    if (this.globalCompositeOperation === 'destination-out') { this._px.fill(0); return; }
    for (let i = 3; i < this._px.length; i += 4) this._px[i] = 255;
  }
  drawImage(src) {
    if (src && src._px && src._px.length === this._px.length) this._px.set(src._px);
  }
  getImageData(x, y, w, h) { return { data: new Uint8ClampedArray(this._px), width: w, height: h }; }
  putImageData(d) { this._px = new Uint8ClampedArray(d.data); }
}

class El {
  constructor(tag, id) {
    this.tagName = (tag || 'div').toUpperCase();
    this.id = id || '';
    this.style = {};
    this.className = '';
    this.dataset = {};
    this.children = [];
    this._text = '';
    this._html = '';
    this.value = '';
    this.disabled = false;
    this.checked = false;
    this.type = '';
    this.files = [];
    this.handlers = {};
    this.width = 0; this.height = 0;
  }
  get textContent() { return this._text; }
  set textContent(v) { this._text = String(v); }
  get innerHTML() { return this._html; }
  set innerHTML(v) { this._html = String(v); if (v === '') this.children = []; }
  addEventListener(t, fn) { (this.handlers[t] = this.handlers[t] || []).push(fn); }
  removeEventListener() {}
  appendChild(c) { this.children.push(c); return c; }
  getContext() { return (this._ctx = this._ctx || new Ctx(this)); }
  getBoundingClientRect() { return { left: 0, top: 0, width: this.width || 500, height: this.height || 700 }; }
  setPointerCapture() {} releasePointerCapture() {}
  click() {
    // support BOTH forms used in the page: .onclick = fn  and addEventListener
    if (typeof this.onclick === 'function') this.onclick({ preventDefault(){}, stopPropagation(){} });
    (this.handlers.click || []).forEach(f => f({ preventDefault(){}, stopPropagation(){} }));
  }
  toBlob(cb) { cb({ size: 3, type: 'image/png' }); }
  toDataURL() { return 'data:image/png;base64,AAAA'; }
  querySelector() { return null; }
}

const IDS = ['apiKey','baseUrl','brush','brushVal','clear','cv','download','drop','editor',
  'erase','eye','file','fit','fitMode','imgInfo','invert','listModels','maskMode','maskStat',
  'model','models','msg','outBox','prompt','quality','run','runAll','addMore','clearList',
  'size','sizeHint','scope','scopeHint','thumbs','batchRow','batchInfo','copyMask','fileName',
  'test','maskTools','engine','engineHint','resolution','resolutionRow','qualityRow',
  // reference-image UI (added with the role-tagged references / slot numbering)
  'refFile','refList','refRow','slotPreview','clearRefs',
  // follow-source-ratio UI
  'followRatio','ratioHint'];

const registry = {};
IDS.forEach(id => { registry[id] = new El(id === 'cv' ? 'canvas' : 'div', id); });
// sensible starting values matching the real page
registry.baseUrl.value = 'https://image-delight.invalid/v1';
registry.apiKey.value = 'sk-x';
registry.model.value = 'gpt-image-2';
registry.prompt.value = 'test prompt';
registry.quality.value = 'low';
registry.size.value = '1024x1536';
registry.fitMode.value = 'pad';
registry.maskMode.value = 'std';
registry.scope.value = 'mask';
registry.brush.value = '36';
registry.cv.width = 837; registry.cv.height = 1243;

const MISSING = [];
const document = {
  getElementById: id => {
    if (!registry[id]) { MISSING.push(id); return null; }
    return registry[id];
  },
  createElement: tag => new El(tag),
  addEventListener() {},
};
const localStorage = {
  getItem() { throw new Error("SecurityError: sandboxed"); },
  setItem() { throw new Error("SecurityError: sandboxed"); },
  removeItem() { throw new Error("SecurityError: sandboxed"); },
};
const fetchCalls = [];
const fetch = async (url, opts) => {
  // capture the FormData entries too, so a test can assert what was actually
  // sent (e.g. that each image in a batch carried its own best-fit size)
  const entries = (opts && opts.body && opts.body._) ? opts.body._.map(e => [e[0], e[1]]) : [];
  fetchCalls.push({ url, hasBody: !!(opts && opts.body), entries });
  const payload = { ok: true, image_b64: 'AAAA', message: 'ok',
                    models: [], image_models: [], slot_map: [] };
  return {
    ok: true,
    json: async () => payload,
    // callEdit() reads the body as text first, then JSON.parse()s it
    text: async () => JSON.stringify(payload)
  };
};
const sentField = (i, key) => {
  const c = fetchCalls[i];
  if (!c) return undefined;
  const hit = c.entries.find(e => e[0] === key);
  return hit ? hit[1] : undefined;
};

// Image stub: fires onload synchronously. Its pixel size follows the file NAME,
// so a test can feed a landscape image ("wide.png") and check that the followed
// size differs from the portrait case.
class ImageStub extends El {
  constructor() {
    super('img');
    this.naturalWidth = 837; this.naturalHeight = 1243;   // default 0.673 ≈ 2:3
  }
  set src(v) {
    this._src = v;
    const n = String(v);
    if (/wide/.test(n)) { this.naturalWidth = 1600; this.naturalHeight = 900; }      // 1.778
    else if (/tall/.test(n)) { this.naturalWidth = 900; this.naturalHeight = 1600; } // 0.5625
    else { this.naturalWidth = 837; this.naturalHeight = 1243; }                     // 0.673
    if (this.onload) setTimeout(() => this.onload(), 0);
  }
  get src() { return this._src; }
}

const sandbox = {
  document, localStorage, fetch, Image: ImageStub,
  // callEdit() creates one of these for its 15-minute timeout; without it every
  // generate path dies before reaching fetch. (Previously the harness silently
  // swallowed this as "异常：AbortController is not defined".)
  AbortController: class { constructor() { this.signal = {}; } abort() {} },
  FormData: class { constructor() { this._ = []; } append(k, v) { this._.push([k, v]); } },
  File: class { constructor(parts, name, opts) { this.name = name; this.type = (opts||{}).type; } },
  URL: { createObjectURL: f => 'blob:' + ((f && f.name) || 'x'), revokeObjectURL() {} },
  confirm: () => true,
  alert: () => {},
  setTimeout, setInterval, clearInterval, clearTimeout,
  console,
  requestAnimationFrame: fn => setTimeout(fn, 0),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.addEventListener = () => {};

const ctxObj = vm.createContext(sandbox);
const FAILS = [];
function check(cond, label, detail) {
  console.log((cond ? '  PASS  ' : '  FAIL  ') + label + (detail ? '  ' + detail : ''));
  if (!cond) FAILS.push(label);
}

try {
  vm.runInContext(js, ctxObj, { filename: 'page.js' });
  console.log('script executed without throwing');
} catch (e) {
  console.log('  FAIL  script threw at load: ' + e.message);
  console.log('  missing element ids requested before the throw: ' +
              JSON.stringify([...new Set(MISSING)]));
  console.log('  stub has these ids: ' + JSON.stringify(Object.keys(registry).sort()));
  process.exit(1);
}
if (MISSING.length) {
  console.log('  NOTE  ids the page asked for but the stub lacks: ' +
              JSON.stringify([...new Set(MISSING)]));
}

const $ = id => registry[id];
const filmCount = () => {
  // films is a top-level `let`; read it back through the context
  return vm.runInContext('typeof films !== "undefined" ? films.length : -1', ctxObj);
};

const mkFile = name => ({ name, type: 'image/png', size: 1000 });

(async () => {
  console.log('\n=== A. pick ONE image, then ANOTHER (the reported bug) ===');
  $('file').files = [mkFile('a.png')];
  $('file').onchange({ target: $('file') });
  await new Promise(r => setTimeout(r, 20));
  check(filmCount() === 1, 'first single pick -> 1 image', 'got ' + filmCount());

  $('file').files = [mkFile('b.png')];
  $('file').onchange({ target: $('file') });
  await new Promise(r => setTimeout(r, 20));
  check(filmCount() === 2, 'second single pick APPENDS -> 2 images', 'got ' + filmCount());

  $('file').files = [mkFile('c.png')];
  $('file').onchange({ target: $('file') });
  await new Promise(r => setTimeout(r, 20));
  check(filmCount() === 3, 'third single pick APPENDS -> 3 images', 'got ' + filmCount());

  console.log('\n=== B. multi-select in one go ===');
  $('file').files = [mkFile('d.png'), mkFile('e.png')];
  $('file').onchange({ target: $('file') });
  await new Promise(r => setTimeout(r, 30));
  check(filmCount() === 5, 'picking 2 files adds 2 -> 5 total', 'got ' + filmCount());

  console.log('\n=== C. thumbnails rendered ===');
  check($('thumbs').children.length === 5, '5 thumbnails in the strip',
        'got ' + $('thumbs').children.length);
  check(/5 /.test($('batchInfo').textContent), 'batch info reports 5',
        JSON.stringify($('batchInfo').textContent));

  console.log('\n=== D. painting registers a mask ===');
  // simulate a drag: pointerdown + a few pointermove
  const pd = $('cv').handlers.pointerdown, pm = $('cv').handlers.pointermove;
  check(!!pd && !!pm, 'pointer handlers are registered');
  if (pd && pm) {
    pd.forEach(f => f({ clientX: 100, clientY: 100, pointerId: 1 }));
    pm.forEach(f => f({ clientX: 200, clientY: 300, pointerId: 1 }));
    await new Promise(r => setTimeout(r, 10));
    check(/覆盖率/.test($('maskStat').textContent), 'coverage readout updated',
          JSON.stringify($('maskStat').textContent));
    const painted = vm.runInContext('hasMask', ctxObj);
    check(painted === true, 'hasMask became true after painting', 'got ' + painted);
  }

  console.log('\n=== E. whole-image mode needs no mask ===');
  $('scope').value = 'whole';
  $('scope').handlers.change.forEach(f => f({ target: $('scope') }));
  check(/不需要涂任何东西/.test($('scopeHint').textContent),
        'scope hint says no painting needed', JSON.stringify($('scopeHint').textContent).slice(0, 60));
  check($('maskTools').style.display === 'none',
        'paint tools are hidden in whole mode', JSON.stringify($('maskTools').style.display));
  check($('maskStat').style.display === 'none',
        'coverage readout hidden in whole mode', JSON.stringify($('maskStat').style.display));
  // the reported failure path: generate with ZERO pixels painted
  const runThrew = (() => {
    try { $('run').onclick(); return null; } catch (e) { return e.message; }
  })();
  await new Promise(r => setTimeout(r, 30));
  check(runThrew === null, 'generate does not throw with no mask painted',
        runThrew ? 'threw: ' + runThrew : '');
  check(!/没有检测到涂改区域/.test($('msg').textContent),
        'no "no mask detected" error in whole mode',
        JSON.stringify($('msg').textContent).slice(0, 60));

  console.log('\n=== G. per-image numbering (batch #N vs request slot 图N) ===');
  // Every image must be visibly labelled with which number it is. Two systems:
  //   #N  = batch order in the "images to edit" queue
  //   图N = position inside one request (图1 content, 图2 red mask, 图3+ refs)

  const numBadges = () => $('thumbs').children
    .map(d => (d.children.find(c => c.className === 'num') || {}).textContent);
  const thumbTitles = () => $('thumbs').children.map(d => d.title || '');
  const refSlotBadges = () => $('refList').children.map(row => {
    const wrap = row.children.find(c => c.className === '' && c.children.length);
    const s = wrap && wrap.children.find(c => c.className === 'slot');
    return s ? s.textContent : null;
  });
  const refCount = () => vm.runInContext('typeof refs !== "undefined" ? refs.length : -1', ctxObj);

  check(JSON.stringify(numBadges()) === JSON.stringify(['#1', '#2', '#3', '#4', '#5']),
        'every queued image carries its batch number', JSON.stringify(numBadges()));
  check(thumbTitles().every((t, i) => t.startsWith(`批量第 ${i + 1} 张`)),
        'thumbnail tooltips also state the batch number',
        JSON.stringify(thumbTitles()[0] || ''));

  // whole mode is active here (section E), so refs start at 图2.
  // refFile binds with addEventListener, unlike #file which uses .onchange.
  $('refFile').files = [mkFile('style_ref.png'), mkFile('pose_ref.png')];
  $('refFile').handlers.change.forEach(f => f({ target: $('refFile') }));
  await new Promise(r => setTimeout(r, 40));
  check(refCount() === 2, 'two reference images loaded -> 2', 'got ' + refCount());
  check(JSON.stringify(refSlotBadges()) === JSON.stringify(['图2', '图3']),
        'whole mode: refs are numbered 图2 + 图3 on their thumbnails',
        JSON.stringify(refSlotBadges()));

  let legend = $('slotPreview').innerHTML;
  // the legend is built with <span>/<b>/<br> markup; strip tags before asserting
  const plainLegend = h => h.replace(/<br\s*\/?>/g, '\n').replace(/<[^>]+>/g, '');
  let plain = plainLegend(legend);
  check(/批量队列/.test(plain) && /单次请求里的图片编号/.test(plain),
        'legend explains BOTH numbering systems');
  check(/#1/.test(plain) && /#5/.test(plain),
        'legend lists every queued image with its batch number');
  check(/图1/.test(plain) && /图2/.test(plain) && /图3/.test(plain),
        'legend lists the request slots 图1..图3');
  check(/style_ref\.png/.test(plain),
        'legend names which file sits in each slot',
        (plain.match(/图3[^\n]*/) || [''])[0].slice(0, 60));
  check(/当前选中/.test(plain), 'legend marks the currently selected batch item');

  // switching to mask mode must push the references to 图3/图4, because the
  // machine-generated red mask guide takes image[1]
  $('scope').value = 'mask';
  $('scope').handlers.change.forEach(f => f({ target: $('scope') }));
  await new Promise(r => setTimeout(r, 20));
  check(JSON.stringify(refSlotBadges()) === JSON.stringify(['图3', '图4']),
        'mask mode: refs shift to 图3 + 图4 (red mask guide takes image[1])',
        JSON.stringify(refSlotBadges()));
  plain = plainLegend($('slotPreview').innerHTML);
  check(/图2 = 红色标记图/.test(plain),
        'legend shows 图2 as the red mask guide in mask mode',
        (plain.match(/图2[^\n]*/) || [''])[0].slice(0, 50));

  // clicking a thumbnail must move the "current" marker in the legend
  $('thumbs').children[2].click();
  await new Promise(r => setTimeout(r, 20));
  plain = plainLegend($('slotPreview').innerHTML);
  check(/#3[^\n]*当前选中/.test(plain),
        'selecting thumbnail #3 marks it as the current 图1 in the legend',
        (plain.match(/#3[^\n]*/) || [''])[0].slice(0, 40));

  console.log('\n=== H. 跟随原图比例（从合法白名单里选最接近的）===');
  // start clean: only the follow-ratio behaviour is under test here
  $('clearList').click();
  $('clearRefs').click();
  $('quality').value = 'low';
  Array.from($('quality').handlers.change || []).forEach(f => f({ target: $('quality') }));
  $('followRatio').checked = true;
  $('followRatio').handlers.change.forEach(f => f({ target: $('followRatio') }));
  check($('size').disabled === true, 'following disables the size select');

  // portrait 837x1243 = 0.673 → low tier has 1024x1536 (2:3, diff 0.007)
  $('file').files = [mkFile('portrait.png')];
  $('file').onchange({ target: $('file') });
  await new Promise(r => setTimeout(r, 30));
  check($('size').value === '1024x1536',
        'portrait 0.673 -> follows to 1024x1536 (the 2:3 slot)',
        'got ' + $('size').value);
  let rh = $('ratioHint').textContent;
  check(/0\.673/.test(rh), 'hint states the source ratio', rh.split('\n')[0]);
  check(/1024x1536/.test(rh), 'hint states the chosen legal size');
  check(/基本吻合|误差 0\.00/.test(rh), 'hint says the ratio is a close fit', rh);
  check(/≈2:3/.test(rh), 'hint names the ratio as ≈2:3');

  // landscape 1600x900 = 1.778 → low tier has 1536x1024 (3:2, diff 0.278)
  $('file').files = [mkFile('wide.png')];
  $('file').onchange({ target: $('file') });
  await new Promise(r => setTimeout(r, 30));
  $('thumbs').children[1].click();          // select the landscape one
  await new Promise(r => setTimeout(r, 20));
  check($('size').value === '1536x1024',
        'selecting a 1.778 landscape re-follows to 1536x1024', 'got ' + $('size').value);
  rh = $('ratioHint').textContent;
  check(/1\.778/.test(rh), 'hint updates to the newly selected image', rh.split('\n')[0]);

  // a tier change must re-follow, and warn that another tier would fit better
  $('quality').value = 'medium';
  Array.from($('quality').handlers.change || []).forEach(f => f({ target: $('quality') }));
  await new Promise(r => setTimeout(r, 20));
  rh = $('ratioHint').textContent;
  check(/1152x2048/.test(rh) || /2048x1152/.test(rh),
        'medium tier re-follows to one of its own legal sizes', rh.split('\n')[1] || rh);
  check(!/1024x1536/.test($('size').value),
        'medium never silently keeps a low-tier size', 'got ' + $('size').value);
  $('quality').value = 'low';
  Array.from($('quality').handlers.change || []).forEach(f => f({ target: $('quality') }));

  // batch: each image must generate at ITS OWN best fit
  $('scope').value = 'whole';
  $('scope').handlers.change.forEach(f => f({ target: $('scope') }));
  await new Promise(r => setTimeout(r, 20));
  fetchCalls.length = 0;
  $('runAll').onclick();
  await new Promise(r => setTimeout(r, 120));
  const sizesSent = fetchCalls.map((c, i) => sentField(i, 'size'));
  const msgAfter = $('msg').textContent;
  check(fetchCalls.length === 2, 'batch sent one request per queued image',
        'got ' + fetchCalls.length + '  msg=' + JSON.stringify(msgAfter).slice(0, 120));
  check(sizesSent[0] === '1024x1536' && sizesSent[1] === '1536x1024',
        'each image in the batch carried its OWN followed size',
        JSON.stringify(sizesSent) + '  msg=' + JSON.stringify(msgAfter).slice(0, 120));

  // turning it off hands the size control back to the user
  $('followRatio').checked = false;
  $('followRatio').handlers.change.forEach(f => f({ target: $('followRatio') }));
  check($('size').disabled === false, 'unticking re-enables the size select');
  check($('ratioHint').textContent === '', 'unticking clears the ratio hint');

  console.log('\n=== F. clear list ===');
  $('clearList').click();
  check(filmCount() === 0, 'clear list empties the queue', 'got ' + filmCount());
  check($('editor').style.display === 'none', 'editor hidden after clearing');

  console.log('\n' + '='.repeat(56));
  console.log('FAILED: ' + FAILS.length + (FAILS.length ? '  ' + JSON.stringify(FAILS) : ' (all passed)'));
  console.log('='.repeat(56));
  process.exit(FAILS.length ? 1 : 0);
})();
