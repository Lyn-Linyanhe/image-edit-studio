"""修正滚轮缩放的基准：以"适应窗口"为 1×，而不是以原图像素为 1×。

用户反馈："放大的第一下太快了，比其他的速度快得多"。

病因（读数即可验证）：原来 paint() 写的是 width = naturalWidth × zf，
而"适应窗口"下显示宽度通常远小于原图宽（大图放进小舞台）。
于是 zf 从 1 迈到 1.06 时，宽度从"适应窗口的宽度"直接跳到"1.06 × 原图宽"——
若适应窗口≈原图宽的 68%，第一下就是 1.06/0.68 ≈ 1.56 倍，之后每格才 6%。

修法：
  · 记下"适应窗口"时的实际显示尺寸 fitW（图片 load 后量一次，切图时重算）
  · paint() 改为 width = fitW × zf → zf=1 就是适应窗口，每格 ×1.06 就是实打实的 6%
  · 顶栏倍率按**原图像素**显示（100% = 1:1），点击图片在"适应窗口 ↔ 100%"之间切
  · 上限同时保证 1:1 一定够得到：maxZ = max(8, naturalWidth/fitW)
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

OLD = (
    "        'let cat=\"all\",visible=[],at=0,zf=1,zfTarget=1,rafId=0,anchor=null;'\n"
    "        'function zoomLabel(){lbZoom.textContent=(zf<=1.001)?\"适应窗口\":Math.round(zf*100)+\"%\";}'\n"
    "        'function paint(){'\n"
    "        'const rect=stage.getBoundingClientRect();'\n"
    "        'const ax=anchor?anchor.cx:rect.width/2,ay=anchor?anchor.cy:rect.height/2;'\n"
    "        'const oldW=lbImg.clientWidth||1,oldH=lbImg.clientHeight||1;'\n"
    "        'const rx=(stage.scrollLeft+ax)/oldW,ry=(stage.scrollTop+ay)/oldH;'\n"
    "        'if(zf<=1.001){lbImg.style.width=\"\";lbImg.classList.remove(\"zoom\");}'\n"
    "        'else{lbImg.style.maxWidth=\"none\";lbImg.classList.add(\"zoom\");'\n"
    "        'const nw=lbImg.naturalWidth||oldW;'\n"
    "        'lbImg.style.width=(nw*zf).toFixed(1)+\"px\";}'\n"
    "        'zoomLabel();'\n"
    "        'if(zf>1.001){stage.scrollLeft=rx*lbImg.clientWidth-ax;'\n"
    "        'stage.scrollTop=ry*lbImg.clientHeight-ay;}}'\n"
    "        'function tick(){'\n"
    "        'if(Math.abs(zfTarget-zf)<0.002){zf=zfTarget;paint();rafId=0;return;}'\n"
    "        'zf+=(zfTarget-zf)*0.22;'\n"
    "        'paint();'\n"
    "        'rafId=requestAnimationFrame(tick);}'\n"
    "        'function zoomTo(f,ev){'\n"
    "        'zfTarget=Math.max(1,Math.min(8,f));'\n"
    "        'if(ev){const r=stage.getBoundingClientRect();'\n"
    "        'anchor={cx:ev.clientX-r.left,cy:ev.clientY-r.top};}'\n"
    "        'else if(!anchor){anchor=null;}'\n"
    "        'if(!rafId)rafId=requestAnimationFrame(tick);}'\n"
    "        'function resetZoom(){'\n"
    "        'if(rafId){cancelAnimationFrame(rafId);rafId=0;}'\n"
    "        'zf=1;zfTarget=1;anchor=null;'\n"
    "        'lbImg.style.width=\"\";lbImg.style.maxWidth=\"\";lbImg.classList.remove(\"zoom\");'\n"
    "        'zoomLabel();}'"
)

NEW = (
    "        'let cat=\"all\",visible=[],at=0,zf=1,zfTarget=1,rafId=0,anchor=null,fitW=0;'\n"
    "        'function maxZ(){const nw=lbImg.naturalWidth||0;'\n"
    "        'return Math.max(8,fitW>0&&nw>0?nw/fitW+1:8);}'\n"
    "        'function zoomLabel(){'\n"
    "        'const nw=lbImg.naturalWidth||0;'\n"
    "        'if(zf<=1.001){lbZoom.textContent=\"适应窗口\";return;}'\n"
    "        'const pct=(nw>0&&fitW>0)?Math.round(zf*fitW/nw*100):Math.round(zf*100);'\n"
    "        'lbZoom.textContent=pct+\"%\";}'\n"
    "        'function paint(){'\n"
    "        'const rect=stage.getBoundingClientRect();'\n"
    "        'const ax=anchor?anchor.cx:rect.width/2,ay=anchor?anchor.cy:rect.height/2;'\n"
    "        'const oldW=lbImg.clientWidth||1,oldH=lbImg.clientHeight||1;'\n"
    "        'const rx=(stage.scrollLeft+ax)/oldW,ry=(stage.scrollTop+ay)/oldH;'\n"
    "        'if(zf<=1.001){lbImg.style.width=\"\";lbImg.classList.remove(\"zoom\");}'\n"
    "        'else{lbImg.style.maxWidth=\"none\";lbImg.classList.add(\"zoom\");'\n"
    "        'const base=fitW||lbImg.naturalWidth||oldW;'\n"
    "        'lbImg.style.width=(base*zf).toFixed(1)+\"px\";}'\n"
    "        'zoomLabel();'\n"
    "        'if(zf>1.001){stage.scrollLeft=rx*lbImg.clientWidth-ax;'\n"
    "        'stage.scrollTop=ry*lbImg.clientHeight-ay;}}'\n"
    "        'function captureFit(){'\n"
    "        'if(lbImg.style.width)return;'\n"                 # 已放大时不动基准
    "        'fitW=lbImg.clientWidth;'\n"
    "        'if(zf>1.001){paint();}}'\n"
    "        'function tick(){'\n"
    "        'if(Math.abs(zfTarget-zf)<0.002){zf=zfTarget;paint();rafId=0;return;}'\n"
    "        'zf+=(zfTarget-zf)*0.22;'\n"
    "        'paint();'\n"
    "        'rafId=requestAnimationFrame(tick);}'\n"
    "        'function zoomTo(f,ev){'\n"
    "        'zfTarget=Math.max(1,Math.min(maxZ(),f));'\n"
    "        'if(ev){const r=stage.getBoundingClientRect();'\n"
    "        'anchor={cx:ev.clientX-r.left,cy:ev.clientY-r.top};}'\n"
    "        'else if(!anchor){anchor=null;}'\n"
    "        'if(!rafId)rafId=requestAnimationFrame(tick);}'\n"
    "        'function oneToOne(){const nw=lbImg.naturalWidth||0;'\n"
    "        'return (nw>0&&fitW>0)?nw/fitW:2;}'\n"
    "        'function resetZoom(){'\n"
    "        'if(rafId){cancelAnimationFrame(rafId);rafId=0;}'\n"
    "        'zf=1;zfTarget=1;anchor=null;fitW=0;'\n"
    "        'lbImg.style.width=\"\";lbImg.style.maxWidth=\"\";lbImg.classList.remove(\"zoom\");'\n"
    "        'zoomLabel();}'"
)

pairs = [
    (OLD, NEW),
    # 点图切"适应窗口 ↔ 100%"（真正的 1:1）
    ("        'lbImg.addEventListener(\"click\",()=>{anchor=null;zoomTo(zfTarget>1.001?1:2,null);});'",
     "        'lbImg.addEventListener(\"click\",()=>{anchor=null;zoomTo(zfTarget>1.001?1:oneToOne(),null);});'"),
    # 图片加载后量一次"适应窗口"尺寸
    ("        'resetZoom();'\n        'lbImg.src=img.dataset.full;'",
     "        'resetZoom();'\n"
     "        'lbImg.onload=()=>{captureFit();};'\n"
     "        'lbImg.src=img.dataset.full;'"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
