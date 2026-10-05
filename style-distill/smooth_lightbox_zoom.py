"""滚轮缩放改为"丝滑"版：按滚轮位移连续改变目标倍率 + 逐帧缓动，并把步进调小。

用户反馈："有点太快了，而且不够丝滑"。
改动：
  · 步进由"每格 ×1.15（固定）"改为**按滚轮位移的指数曲线**：factor = exp(-Δy × 0.0006)
    → 一格（≈100px）约 ×1.06（原来是 1.15），触控板的小位移则是连续微调
  · 目标倍率 zfTarget 与当前倍率 zf 分离，用 requestAnimationFrame **逐帧缓动**（每帧逼近 22%），
    停止时自动收尾到精确值；滚动锚点逐帧校正，所以放大过程中光标下的那一块始终不动
  · deltaMode 归一化（行/页 → 像素），避免不同设备步长差异
  · 点图切 1:1 也走同一套缓动（不再是硬跳）
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

OLD_ZOOM = (
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
    "        'stage.scrollTop=ry*lbImg.clientHeight-cy;}}'"
)

NEW_ZOOM = (
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

pairs = [
    (OLD_ZOOM, NEW_ZOOM),
    # 切图重置改为调用 resetZoom()
    ("        'lbImg.classList.remove(\"zoom\");lbImg.style.width=\"\";lbImg.style.maxWidth=\"\";zf=1;zoomLabel();'",
     "        'resetZoom();'"),
    # 点图切 1:1 走缓动
    ("        'lbImg.addEventListener(\"click\",()=>applyZoom(zf>1.001?1:2,null));'\n"
     "        'stage.addEventListener(\"wheel\",e=>{if(lb.hidden)return;'\n"
     "        'e.preventDefault();applyZoom(zf*(e.deltaY<0?1.15:1/1.15),e);},{passive:false});'",
     "        'lbImg.addEventListener(\"click\",()=>{anchor=null;zoomTo(zfTarget>1.001?1:2,null);});'\n"
     "        'stage.addEventListener(\"wheel\",e=>{if(lb.hidden)return;'\n"
     "        'e.preventDefault();'\n"
     "        'let dy=e.deltaY;'\n"
     "        'if(e.deltaMode===1)dy*=16;else if(e.deltaMode===2)dy*=100;'\n"
     "        'zoomTo(zfTarget*Math.exp(-dy*0.0006),e);},{passive:false});'"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

# close_() 也要收尾动画，避免关掉后 rAF 还在跑
old_close = ("        'function close_(){lb.hidden=true;lbImg.removeAttribute(\"src\");'\n"
             "        'document.body.classList.remove(\"locked\");}'")
new_close = ("        'function close_(){resetZoom();lb.hidden=true;lbImg.removeAttribute(\"src\");'\n"
             "        'document.body.classList.remove(\"locked\");}'")
n = t.count(old_close)
print(f"  close_ 锚点命中 {n} 次")
assert n == 1, "close_ 锚点不是 1 处"
t = t.replace(old_close, new_close)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
