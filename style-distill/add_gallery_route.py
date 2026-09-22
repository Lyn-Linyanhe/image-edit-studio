"""给本地图片服务 mask_edit_app.py 加一个「图片」画廊页（快捷打开相关图片）。

动机（已核实）：GUI 的"本轮产出文件"清单**只从 write / edit / str_replace_editor 的调用参数里取条目**
（见 dsh-client-ui-deliverables 的类型注释："Reads, unsupported tools, malformed calls, and failed
results contribute nothing"），而本项目的图是**脚本生成的**（python run_round.py）→
所以正文里用行内代码写的图片路径**不会变成可点击链接**。
画廊由本地服务自己提供：按修改时间倒序列出工作区图片，点缩略图即在新标签打开原图。

为什么加在这里而不是插件节点半边：插件的 node half 改了必须重启 `dsh web`（会让当前会话页面断开），
而本服务是**按需拉起**的本地进程，重启它不影响 GUI。

锚点必须命中 1 次；写回前 compile 校验。
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

HELPERS = '''

# --------------------------------------------------------------------------
# 画廊（快捷打开相关图片）
# --------------------------------------------------------------------------
# 按修改时间倒序列出工作区里的图片；点缩略图在新标签打开原图，另给一个"复制路径"按钮。
# 只服务白名单根目录内的图片后缀，避免变成任意文件读取。
GALLERY_ROOTS = [
    r"C:\\Users\\typ\\Desktop\\mantu\\style-distill",
    r"C:\\Users\\typ\\Desktop\\mantu\\compose",
]
GALLERY_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
GALLERY_MAX = 240
GALLERY_REL_BASE = r"C:\\Users\\typ\\Desktop\\mantu"


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
                found.append((st.st_mtime, st.st_size, full))
    found.sort(key=lambda r: r[0], reverse=True)
    return found[:GALLERY_MAX]


def gallery_html() -> str:
    import html
    import os
    import time

    cards = []
    for mtime, size, full in _gallery_scan():
        try:
            rel = os.path.relpath(full, GALLERY_REL_BASE).replace("\\\\", "/")
        except ValueError:
            rel = full
        q = urllib.parse.quote(full)
        cards.append(
            '<figure class="card">'
            f'<a href="/gallery/img?p={q}" target="_blank" rel="noopener">'
            f'<img loading="lazy" src="/gallery/img?p={q}" alt="{html.escape(os.path.basename(full))}">'
            '</a>'
            f'<figcaption><b>{html.escape(os.path.basename(full))}</b>'
            f'<span class="meta">{time.strftime("%m-%d %H:%M", time.localtime(mtime))}'
            f' · {max(1, size // 1024)} KB</span>'
            f'<span class="path">{html.escape(rel)}</span>'
            f'<button type="button" data-copy="{html.escape(full, quote=True)}">复制路径</button>'
            '</figcaption></figure>')

    return (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>图片 · mantu</title><style>'
        'body{margin:0;background:#14161a;color:#e8eaed;font:14px/1.5 system-ui,"Segoe UI",sans-serif}'
        'header{position:sticky;top:0;z-index:2;background:#1b1e24;border-bottom:1px solid #2b3038;'
        'padding:10px 14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}'
        'h1{font-size:15px;margin:0;font-weight:600}'
        'input{background:#0f1115;border:1px solid #333a44;color:inherit;border-radius:6px;padding:6px 10px;'
        'font:inherit;min-width:240px}'
        '.hint{color:#98a2b3;font-size:12px}'
        'main{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;padding:14px}'
        '.card{margin:0;background:#1b1e24;border:1px solid #2b3038;border-radius:8px;overflow:hidden}'
        '.card img{display:block;width:100%;height:200px;object-fit:contain;background:#0f1115}'
        'figcaption{padding:8px;display:grid;gap:2px}'
        'figcaption b{font-size:12.5px;word-break:break-all}'
        '.meta{color:#98a2b3;font-size:11.5px}'
        '.path{color:#7d8794;font-size:11px;word-break:break-all}'
        'button{margin-top:6px;background:#22262d;border:1px solid #333a44;color:#cfd6df;border-radius:5px;'
        'padding:4px 8px;font:inherit;font-size:12px;cursor:pointer}'
        'button:hover{background:#2b3038}'
        '</style></head><body>'
        '<header><h1>图片</h1>'
        '<input id="q" placeholder="按文件名 / 路径筛选（如 v2、round_arcade）">'
        f'<span class="hint" id="count">共 {len(cards)} 张，按修改时间倒序；点缩略图在新标签打开原图</span>'
        '</header><main id="grid">'
        + "".join(cards) +
        '</main><script>'
        'const q=document.getElementById("q"),grid=document.getElementById("grid"),'
        'cards=[...grid.querySelectorAll(".card")],count=document.getElementById("count");'
        'q.addEventListener("input",()=>{const s=q.value.trim().toLowerCase();let n=0;'
        'for(const c of cards){const hit=!s||c.textContent.toLowerCase().includes(s);'
        'c.style.display=hit?"":"none";if(hit)n++;}count.textContent=`匹配 ${n} 张`;});'
        'grid.addEventListener("click",async(e)=>{const b=e.target.closest("button[data-copy]");'
        'if(!b)return;e.preventDefault();try{await navigator.clipboard.writeText(b.dataset.copy);'
        'b.textContent="已复制";setTimeout(()=>b.textContent="复制路径",1200);}'
        'catch(_){window.prompt("复制这条路径：",b.dataset.copy);}});'
        '</script></body></html>')
'''

IMG_METHOD = '''
    def _gallery_image(self, wanted: str):
        """服务白名单根目录内的图片文件（防目录穿越：解析后必须落在根内）。"""
        import os

        p = os.path.abspath(wanted or "")
        allowed = False
        for root in GALLERY_ROOTS:
            root_abs = os.path.abspath(root)
            try:
                if os.path.commonpath([p, root_abs]) == root_abs:
                    allowed = True
                    break
            except ValueError:
                continue          # 不同盘符等
        ext = os.path.splitext(p)[1].lower()
        if not allowed or ext not in GALLERY_EXTS or not os.path.isfile(p):
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        try:
            with open(p, "rb") as f:
                data = f.read()
        except OSError as e:
            return self._send(500, str(e).encode("utf-8"), "text/plain; charset=utf-8")
        ctype = ("image/png" if ext == ".png"
                 else "image/jpeg" if ext in (".jpg", ".jpeg")
                 else "image/webp" if ext == ".webp" else "image/gif")
        return self._send(200, data, ctype)
'''

ROUTE = '''        elif path == "/gallery":
            self._send(200, gallery_html().encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/gallery/img":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self._gallery_image((qs.get("p") or [""])[0])
        else:'''

pairs = [
    # 1) 模块级：画廊扫描与页面
    ("\n# --------------------------------------------------------------------------\n"
     "# HTTP server\n"
     "# --------------------------------------------------------------------------\n"
     "class Handler(BaseHTTPRequestHandler):",
     HELPERS + "\n\n# --------------------------------------------------------------------------\n"
     "# HTTP server\n"
     "# --------------------------------------------------------------------------\n"
     "class Handler(BaseHTTPRequestHandler):"),
    # 2) Handler 方法：按白名单服务图片
    ("    def do_OPTIONS(self):\n        self._send(204, b\"\")",
     IMG_METHOD + "\n    def do_OPTIONS(self):\n        self._send(204, b\"\")"),
    # 3) 路由分支
    ('        elif path == "/favicon.ico":\n'
     '            self._send(204, b"")\n'
     '        else:',
     '        elif path == "/favicon.ico":\n'
     '            self._send(204, b"")\n'
     + ROUTE),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:56]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
print("  已写入", P)

# 写回后立即 compile 校验（SKILL.md 纪律）
import py_compile                                    # noqa: E402
py_compile.compile(str(P), doraise=True)
print("  编译通过")
