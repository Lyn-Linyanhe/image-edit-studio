"""把画廊改成页内灯箱预览：点图不跳转，可 ←/→ 连续翻图。

替换范围只有 gallery_html() 这一个函数（锚点：函数头 → HTTP server 段标题）。
注意：CSS 与 JS 一律放在**非 f-string** 里，避免 Python 把 CSS 的花括号当占位符。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

START = "def gallery_html() -> str:"
END = ("\n\n# --------------------------------------------------------------------------\n"
       "# HTTP server\n"
       "# --------------------------------------------------------------------------")

NEW = r'''def gallery_html() -> str:
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
            f'<img class="thumb" loading="lazy" src="/gallery/img?p={q}"'
            f' data-full="/gallery/img?p={q}"'
            f' data-file="{html.escape(full, quote=True)}"'
            f' data-rel="{html.escape(rel, quote=True)}"'
            f' data-name="{html.escape(rel.rsplit("/", 1)[-1], quote=True)}"'
            f' alt="{html.escape(rel)}">'
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

    head = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>图片 · mantu</title><style>'
        'body{margin:0;background:#14161a;color:#e8eaed;font:14px/1.5 system-ui,"Segoe UI",sans-serif}'
        'body.locked{overflow:hidden}'
        'header{position:sticky;top:0;z-index:3;background:#1b1e24;border-bottom:1px solid #2b3038;'
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
        '.thumb{display:block;width:100%;height:200px;object-fit:contain;background:#0f1115;cursor:zoom-in}'
        '.thumb:hover{outline:2px solid #3f7fe0;outline-offset:-2px}'
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
        '#lb{position:fixed;inset:0;z-index:9;background:rgba(8,10,13,.94);display:flex;'
        'flex-direction:column}'
        '#lb[hidden]{display:none}'
        '.lb-bar{display:flex;gap:10px;align-items:center;padding:8px 12px;background:#1b1e24;'
        'border-bottom:1px solid #2b3038;flex-wrap:wrap}'
        '.lb-bar .name{font-weight:600}'
        '.lb-bar .rel{color:#7d8794;font-size:11.5px;word-break:break-all}'
        '.lb-bar .sp{flex:1}'
        '.lb-bar a{color:#8fb8ff;text-decoration:none;border:1px solid #333a44;border-radius:5px;'
        'padding:4px 8px;font-size:12px}'
        '.lb-stage{flex:1;position:relative;overflow:auto;display:flex;align-items:center;justify-content:center}'
        '#lb-img{max-width:100%;max-height:100%;object-fit:contain;cursor:zoom-in}'
        '#lb-img.zoom{max-width:none;max-height:none;cursor:zoom-out}'
        '.lb-nav{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:64px;'
        'background:rgba(34,38,45,.85);border:1px solid #333a44;color:#e8eaed;font-size:20px;'
        'border-radius:8px;cursor:pointer;margin:0}'
        '#lb-prev{left:10px}'
        '#lb-next{right:10px}'
        '.lb-pos{color:#98a2b3;font-size:12px;font-variant-numeric:tabular-nums}'
        '</style></head><body>'
        '<header><h1>图片</h1>'
        f'<div class="tabs">{tabs}</div>'
        '<input id="q" placeholder="按文件名 / 路径筛选（如 v2、round_arcade）">'
        f'<span class="hint" id="hint">共 {counts["all"]} 张；'
        f'成果与局部一张不落，过程只取最新 {GALLERY_PROCESS_CAP} 张 · 点图页内预览，←/→ 翻图</span>'
        '</header><main id="grid">'
    )

    lightbox = (
        '</main>'
        '<div id="lb" hidden>'
        '<div class="lb-bar">'
        '<span class="name" id="lb-name"></span>'
        '<span class="rel" id="lb-rel"></span>'
        '<span class="sp"></span>'
        '<span class="lb-pos" id="lb-pos"></span>'
        '<a id="lb-raw" href="#" target="_blank" rel="noopener">在新标签打开原图</a>'
        '<button type="button" id="lb-copy">复制路径</button>'
        '<button type="button" id="lb-close">关闭 (Esc)</button>'
        '</div>'
        '<div class="lb-stage" id="lb-stage">'
        '<button type="button" class="lb-nav" id="lb-prev" aria-label="上一张">‹</button>'
        '<img id="lb-img" alt="">'
        '<button type="button" class="lb-nav" id="lb-next" aria-label="下一张">›</button>'
        '</div></div>'
        '<script>'
        'const q=document.getElementById("q"),grid=document.getElementById("grid"),'
        'hint=document.getElementById("hint"),'
        'cards=[...grid.querySelectorAll(".card")],tabs=[...document.querySelectorAll(".tab")],'
        'lb=document.getElementById("lb"),lbImg=document.getElementById("lb-img"),'
        'lbName=document.getElementById("lb-name"),lbRel=document.getElementById("lb-rel"),'
        'lbRaw=document.getElementById("lb-raw"),lbCopy=document.getElementById("lb-copy"),'
        'lbPos=document.getElementById("lb-pos");'
        'let cat="all",visible=[],at=0;'
        'function refresh(){visible=cards.filter(c=>c.style.display!=="none");}'
        'function apply(){const s=q.value.trim().toLowerCase();let total=0,shown=0;'
        'for(const c of cards){const okCat=(cat==="all"||c.dataset.cat===cat);'
        'if(okCat)total++;const hit=okCat&&(!s||c.textContent.toLowerCase().includes(s));'
        'c.style.display=hit?"":"none";if(hit)shown++;}'
        'refresh();'
        'hint.textContent=`显示 ${shown} / ${total} 张`+(s?`（筛选「${q.value.trim()}」）`:"")'
        '+` · 点图页内预览，←/→ 翻图`;'
        'for(const t of tabs)t.classList.toggle("on",t.dataset.cat===cat);'
        'if(!lb.hidden)show(at);}'
        'function show(i){if(!visible.length){close_();return;}'
        'at=(i%visible.length+visible.length)%visible.length;'
        'const c=visible[at],img=c.querySelector("img");'
        'lbImg.classList.remove("zoom");'
        'lbImg.src=img.dataset.full;'
        'lbName.textContent=img.dataset.name;'
        'lbRel.textContent=img.dataset.rel;'
        'lbRaw.href=img.dataset.full;'
        'lbCopy.dataset.copy=img.dataset.file;'
        'lbPos.textContent=(at+1)+" / "+visible.length;'
        'lb.hidden=false;document.body.classList.add("locked");}'
        'function close_(){lb.hidden=true;lbImg.removeAttribute("src");'
        'document.body.classList.remove("locked");}'
        'for(const t of tabs)t.addEventListener("click",()=>{cat=t.dataset.cat;apply();});'
        'q.addEventListener("input",apply);'
        'grid.addEventListener("click",e=>{'
        'if(e.target.closest("button[data-copy]")){'
        'const b=e.target.closest("button[data-copy]");'
        'navigator.clipboard.writeText(b.dataset.copy).then(()=>{'
        'b.textContent="已复制";setTimeout(()=>b.textContent="复制路径",1200);})'
        '.catch(()=>window.prompt("复制这条路径：",b.dataset.copy));return;}'
        'const c=e.target.closest(".card");if(!c)return;refresh();show(visible.indexOf(c));});'
        'document.getElementById("lb-close").addEventListener("click",close_);'
        'document.getElementById("lb-prev").addEventListener("click",()=>show(at-1));'
        'document.getElementById("lb-next").addEventListener("click",()=>show(at+1));'
        'lbImg.addEventListener("click",()=>lbImg.classList.toggle("zoom"));'
        'lbCopy.addEventListener("click",()=>{'
        'navigator.clipboard.writeText(lbCopy.dataset.copy||"").then(()=>{'
        'lbCopy.textContent="已复制";setTimeout(()=>lbCopy.textContent="复制路径",1200);})'
        '.catch(()=>window.prompt("复制这条路径：",lbCopy.dataset.copy||""));});'
        'lb.addEventListener("click",e=>{if(e.target===lb)close_();});'
        'document.addEventListener("keydown",e=>{if(lb.hidden)return;'
        'if(e.key==="Escape")close_();'
        'else if(e.key==="ArrowRight"){e.preventDefault();show(at+1);}'
        'else if(e.key==="ArrowLeft"){e.preventDefault();show(at-1);}});'
        'apply();'
        '</script></body></html>'
    )

    return head + "".join(cards) + lightbox
'''

assert t.count(START) == 1, "函数起点锚点不是 1 处"
assert t.count(END) == 1, "段尾锚点不是 1 处"
i0, i1 = t.index(START), t.index(END)
P.write_text(t[:i0] + NEW + t[i1:], encoding="utf-8")
print(f"  已替换 gallery_html：{i1 - i0} 字 → {len(NEW)} 字")
py_compile.compile(str(P), doraise=True)
print("  编译通过")
