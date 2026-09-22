"""灯箱加滚轮缩放（以光标为中心），并把"点图切 1:1"保留为快捷键。

设计：
  · 缩放系数 zf：1 = 适应窗口（沿用原来的 CSS 自适应），>1 = 按像素放大（最长边不超过原图 8 倍）
  · 滚轮以光标为锚点：先记下光标处的相对位置，改完后把滚动条调回去，视觉上"定点放大"
  · 缩回 1 时清掉内联尺寸，回到自适应；切图时重置
  · 顶栏显示当前倍率（适应窗口 / 120% …）
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    # 1) CSS：倍率标签
    (".lb-pos{color:#98a2b3;font-size:12px;font-variant-numeric:tabular-nums}",
     ".lb-pos{color:#98a2b3;font-size:12px;font-variant-numeric:tabular-nums}"
     ".lb-zoom{color:#cfd6df;font-size:12px;font-variant-numeric:tabular-nums;"
     "min-width:56px;text-align:right}"),
    # 2) 顶栏加倍率显示
    ("        '<span class=\"lb-pos\" id=\"lb-pos\"></span>'",
     "        '<span class=\"lb-pos\" id=\"lb-pos\"></span>'\n"
     "        '<span class=\"lb-zoom\" id=\"lb-zoom\">适应窗口</span>'"),
    # 3) 取元素
    ("        'lbPos=document.getElementById(\"lb-pos\");'",
     "        'lbPos=document.getElementById(\"lb-pos\"),'\n"
     "        'lbZoom=document.getElementById(\"lb-zoom\"),'\n"
     "        'stage=document.getElementById(\"lb-stage\");'"),
    # 4) 状态与缩放函数
    ("        'let cat=\"all\",visible=[],at=0;'",
     "        'let cat=\"all\",visible=[],at=0,zf=1;'\n"
     "        'function zoomLabel(){lbZoom.textContent=(zf<=1.001)?\"适应窗口\":Math.round(zf*100)+\"%\";}'\n"
     "        'function applyZoom(f,ev){'\n"
     "        'f=Math.max(1,Math.min(8,f));'\n"
     "        'const rect=stage.getBoundingClientRect();'\n"
     "        'const oldW=lbImg.clientWidth||1,oldH=lbImg.clientHeight||1;'\n"
     "        'const cx=ev?ev.clientX-rect.left:rect.width/2;'\n"
     "        'const cy=ev?ev.clientY-rect.top:rect.height/2;'\n"
     "        'const rx=(stage.scrollLeft+cx)/oldW,ry=(stage.scrollTop+cy)/oldH;'\n"
     "        'zf=f;'\n"
     "        'if(zf<=1.001){lbImg.style.width=\"\";lbImg.classList.remove(\"zoom\");}'\n"
     "        'else{lbImg.style.maxWidth=\"none\";lbImg.classList.add(\"zoom\");'\n"
     "        'const nw=lbImg.naturalWidth||oldW,nh=lbImg.naturalHeight||oldH;'\n"
     "        'lbImg.style.width=Math.round(nw*zf)+\"px\";}'\n"
     "        'zoomLabel();'\n"
     "        'if(zf>1.001){stage.scrollLeft=rx*lbImg.clientWidth-cx;'\n"
     "        'stage.scrollTop=ry*lbImg.clientHeight-cy;}}'"),
    # 5) 切图时重置缩放
    ("        'lbImg.classList.remove(\"zoom\");'\n        'lbImg.src=img.dataset.full;'",
     "        'lbImg.classList.remove(\"zoom\");lbImg.style.width=\"\";lbImg.style.maxWidth=\"\";zf=1;zoomLabel();'\n"
     "        'lbImg.src=img.dataset.full;'"),
    # 6) 点图切 1:1 ↔ 适应（保留快捷键，走同一套状态）
    ("        'lbImg.addEventListener(\"click\",()=>lbImg.classList.toggle(\"zoom\"));'",
     "        'lbImg.addEventListener(\"click\",()=>applyZoom(zf>1.001?1:2,null));'\n"
     "        'stage.addEventListener(\"wheel\",e=>{if(lb.hidden)return;'\n"
     "        'e.preventDefault();applyZoom(zf*(e.deltaY<0?1.15:1/1.15),e);},{passive:false});'"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
