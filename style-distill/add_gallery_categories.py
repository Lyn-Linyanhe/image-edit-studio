"""给画廊加分类（全部/成果/局部/过程），并修掉"上限把旧交付件挤掉"的问题。

依据（先测出来的，不是猜的）：两个根目录下共 278 张图，而画廊上限 240 张、按时间倒序 →
round_manga 那批较旧的交付件会被挤出列表。所以改为：
  成果 / 局部 不封顶；只对"过程"取最新的 N 张。
分类规则实测分布：成果 43、局部 19、过程 216（旧规则）；本版把 lab 与 checks 归入"局部"。
"""
from __future__ import annotations
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

START = ("# --------------------------------------------------------------------------\n"
         "# 画廊（快捷打开相关图片）\n"
         "# --------------------------------------------------------------------------")
END = ("\n\n# --------------------------------------------------------------------------\n"
       "# HTTP server\n"
       "# --------------------------------------------------------------------------")

NEW = r'''# --------------------------------------------------------------------------
# 画廊（快捷打开相关图片）
# --------------------------------------------------------------------------
# 按修改时间倒序列出工作区里的图片，并分三类：
#   成果 = 交付件（round 根层的 out_*、compose 的 out/final/deliver 目录）
#   局部 = 局部改图与对照件（round_*/lab 的改图实验件、checks 的检查图、
#          以及名字里带 redmark / _zoom_ / _sheet / contact / palette / _crop 的对照物）
#   过程 = 其余（work/、input/、target*、ref_*、round_lib、compose 杂项等）
# 规则写在 gallery_category() 里，页面上每张卡片都带分类标签，便于核对与调整。
# 只服务白名单根目录内的图片后缀，避免变成任意文件读取。
GALLERY_ROOTS = [
    rf"{_MANTU_ROOT_STR}\style-distill",
    rf"{_MANTU_ROOT_STR}\compose",
]
GALLERY_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
GALLERY_REL_BASE = _MANTU_ROOT_STR
GALLERY_SCAN_LIMIT = 3000          # 扫描上限（纯安全阀）
GALLERY_PROCESS_CAP = 120          # 只有"过程"封顶：成果与局部一张不落

CATEGORIES = (("all", "全部"), ("deliver", "成果"), ("detail", "局部"), ("process", "过程"))
CAT_LABEL = {"deliver": "成果", "detail": "局部", "process": "过程"}
DETAIL_DIRS = {"lab", "checks"}
DETAIL_HINTS = ("redmark", "_zoom_", "_sheet", "contact", "palette", "_crop")
DELIVER_DIRS = {"out", "out2", "final", "final2", "deliver"}


def gallery_category(rel: str) -> str:
    """按路径特征分到 成果 / 局部 / 过程（顺序即优先级）。"""
    import os

    name = os.path.basename(rel).lower()
    segs = [s.lower() for s in rel.replace("\\", "/").split("/")]
    dirs = segs[:-1]
    in_detail = bool(set(dirs) & DETAIL_DIRS)
    if (name.startswith("out_") and "work" not in dirs and not in_detail
            and any(d.startswith("round_") for d in dirs)):
        return "deliver"
    if set(dirs) & DELIVER_DIRS:
        return "deliver"
    if in_detail or any(h in name for h in DETAIL_HINTS):
        return "detail"
    return "process"


def _gallery_scan():
    import os

    found = []
    for root in GALLERY_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in ("node_modules", "__pycache__", ".git")]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in GALLERY_EXTS:
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                try:
                    rel = os.path.relpath(full, GALLERY_REL_BASE).replace("\\", "/")
                except ValueError:
                    rel = full.replace("\\", "/")
                found.append({"mtime": st.st_mtime, "size": st.st_size,
                              "full": full, "rel": rel,
                              "cat": gallery_category(rel)})
                if len(found) >= GALLERY_SCAN_LIMIT:
                    break
    found.sort(key=lambda r: r["mtime"], reverse=True)
    return found


def gallery_select():
    """成果与局部全取；过程只取最新 GALLERY_PROCESS_CAP 张。"""
    rows = _gallery_scan()
    kept, process_seen = [], 0
    for row in rows:
        if row["cat"] == "process":
            process_seen += 1
            if process_seen > GALLERY_PROCESS_CAP:
                continue
        kept.append(row)
    counts = {key: 0 for key, _ in CATEGORIES}
    counts["all"] = len(kept)
    for row in kept:
        counts[row["cat"]] = counts.get(row["cat"], 0) + 1
    return kept, counts


def gallery_html() -> str:
    import html
    import time

    rows, counts = gallery_select()
    cards = []
    for row in rows:
        full, rel = row["full"], row["rel"]
        cat = row["cat"]
        q = urllib.parse.quote(full)
        cards.append(
            f'<figure class="card" data-cat="{cat}">'
            f'<a href="/gallery/img?p={q}" target="_blank" rel="noopener">'
            f'<img loading="lazy" src="/gallery/img?p={q}" alt="{html.escape(rel)}">'
            '</a>'
            f'<figcaption><span class="chip c-{cat}">{CAT_LABEL.get(cat, cat)}</span>'
            f'<b>{html.escape(rel.rsplit("/", 1)[-1])}</b>'
            f'<span class="meta">{time.strftime("%m-%d %H:%M", time.localtime(row["mtime"]))}'
            f' · {max(1, row["size"] // 1024)} KB</span>'
            f'<span class="path">{html.escape(rel)}</span>'
            f'<button type="button" data-copy="{html.escape(full, quote=True)}">复制路径</button>'
            '</figcaption></figure>')

    tabs = "".join(
        f'<button type="button" class="tab{" on" if key == "all" else ""}" data-cat="{key}">'
        f'{label}<span class="n">{counts.get(key, 0)}</span></button>'
        for key, label in CATEGORIES)

    return (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>图片 · mantu</title><style>'
        'body{margin:0;background:#14161a;color:#e8eaed;font:14px/1.5 system-ui,"Segoe UI",sans-serif}'
        'header{position:sticky;top:0;z-index:2;background:#1b1e24;border-bottom:1px solid #2b3038;'
        'padding:10px 14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}'
        'h1{font-size:15px;margin:0;font-weight:600}'
        '.tabs{display:flex;gap:6px}'
        '.tab{background:#22262d;border:1px solid #333a44;color:#cfd6df;border-radius:6px;'
        'padding:4px 10px;font:inherit;font-size:13px;cursor:pointer;display:inline-flex;gap:6px}'
        '.tab:hover{background:#2b3038}'
        '.tab.on{background:#2f6fd0;border-color:#3f7fe0;color:#fff}'
        '.tab .n{opacity:.75;font-variant-numeric:tabular-nums}'
        'input{background:#0f1115;border:1px solid #333a44;color:inherit;border-radius:6px;'
        'padding:6px 10px;font:inherit;min-width:220px}'
        '.hint{color:#98a2b3;font-size:12px}'
        'main{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;padding:14px}'
        '.card{margin:0;background:#1b1e24;border:1px solid #2b3038;border-radius:8px;overflow:hidden}'
        '.card img{display:block;width:100%;height:200px;object-fit:contain;background:#0f1115}'
        'figcaption{padding:8px;display:grid;gap:2px}'
        'figcaption b{font-size:12.5px;word-break:break-all}'
        '.chip{justify-self:start;font-size:11px;padding:1px 6px;border-radius:10px;border:1px solid}'
        '.c-deliver{color:#8fe388;border-color:#2f5d33}'
        '.c-detail{color:#ffd27f;border-color:#5d4a2f}'
        '.c-process{color:#9fb4cc;border-color:#33445d}'
        '.meta{color:#98a2b3;font-size:11.5px}'
        '.path{color:#7d8794;font-size:11px;word-break:break-all}'
        'button{margin-top:6px;background:#22262d;border:1px solid #333a44;color:#cfd6df;border-radius:5px;'
        'padding:4px 8px;font:inherit;font-size:12px;cursor:pointer}'
        'button:hover{background:#2b3038}'
        '</style></head><body>'
        '<header><h1>图片</h1>'
        f'<div class="tabs">{tabs}</div>'
        '<input id="q" placeholder="按文件名 / 路径筛选（如 v2、round_arcade）">'
        f'<span class="hint" id="hint">共 {counts["all"]} 张；'
        f'成果与局部一张不落，过程只取最新 {GALLERY_PROCESS_CAP} 张</span>'
        '</header><main id="grid">'
        + "".join(cards) +
        '</main><script>'
        'const q=document.getElementById("q"),grid=document.getElementById("grid"),'
        'hint=document.getElementById("hint"),'
        'cards=[...grid.querySelectorAll(".card")],tabs=[...document.querySelectorAll(".tab")];'
        'let cat="all";'
        'function apply(){const s=q.value.trim().toLowerCase();let n=0,total=0,shown=0;'
        'for(const c of cards){const okCat=(cat==="all"||c.dataset.cat===cat);'
        'if(okCat)total++;const hit=okCat&&(!s||c.textContent.toLowerCase().includes(s));'
        'c.style.display=hit?"":"none";if(hit){shown++;}}'
        'hint.textContent=`显示 ${shown} / ${total} 张`+(s?`（筛选「${q.value.trim()}」）`:"");'
        'for(const t of tabs)t.classList.toggle("on",t.dataset.cat===cat);}'
        'for(const t of tabs)t.addEventListener("click",()=>{cat=t.dataset.cat;apply();});'
        'q.addEventListener("input",apply);'
        'grid.addEventListener("click",async(e)=>{const b=e.target.closest("button[data-copy]");'
        'if(!b)return;e.preventDefault();try{await navigator.clipboard.writeText(b.dataset.copy);'
        'b.textContent="已复制";setTimeout(()=>b.textContent="复制路径",1200);}'
        'catch(_){window.prompt("复制这条路径：",b.dataset.copy);}});'
        'apply();'
        '</script></body></html>')
'''

assert t.count(START) == 1, "画廊起点锚点不是 1 处"
assert t.count(END) == 1, "画廊终点锚点不是 1 处"
i0 = t.index(START)
i1 = t.index(END)
t2 = t[:i0] + NEW + t[i1:]
P.write_text(t2, encoding="utf-8")
print(f"  已替换画廊整段：{i1 - i0} 字 → {len(NEW)} 字")
py_compile.compile(str(P), doraise=True)
print("  编译通过")
