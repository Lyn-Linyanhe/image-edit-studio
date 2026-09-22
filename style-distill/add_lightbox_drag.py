"""灯箱放大后加"按住拖动平移"。

设计：
  · 只在放大状态（zf>1）可拖：适应窗口时拖动无意义，且空白处点击是"关闭"
  · 用 Pointer Events + setPointerCapture：拖出图片范围也不断线
  · 拖动超过 3px 记为"拖过"，用于**抑制随后的 click**（否则拖完会误触发"切 1:1"）
  · 光标：适应窗口 zoom-in；放大后 grab；拖动中 grabbing
  · touch-action:none（放大时）让触屏拖动不被页面滚动抢走
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    # 1) CSS：光标与触控
    ("'#lb-img.zoom{max-width:none;max-height:none;cursor:zoom-out}'",
     "'#lb-img.zoom{max-width:none;max-height:none;cursor:grab;touch-action:none}'\n"
     "        '#lb-img.dragging{cursor:grabbing}'"),
    # 2) 拖动逻辑 + 抑制误触
    ("        'lbImg.addEventListener(\"click\",()=>{anchor=null;zoomTo(zfTarget>1.001?1:oneToOne(),null);});'",
     "        'let dragging=false,dragMoved=false,dragX=0,dragY=0,dragSL=0,dragST=0;'\n"
     "        'lbImg.addEventListener(\"dragstart\",e=>e.preventDefault());'\n"
     "        'lbImg.addEventListener(\"pointerdown\",e=>{'\n"
     "        'if(lb.hidden||zf<=1.001)return;'\n"
     "        'dragging=true;dragMoved=false;'\n"
     "        'dragX=e.clientX;dragY=e.clientY;'\n"
     "        'dragSL=stage.scrollLeft;dragST=stage.scrollTop;'\n"
     "        'try{lbImg.setPointerCapture(e.pointerId);}catch(_){}'\n"
     "        'lbImg.classList.add(\"dragging\");e.preventDefault();});'\n"
     "        'lbImg.addEventListener(\"pointermove\",e=>{'\n"
     "        'if(!dragging)return;'\n"
     "        'const dx=e.clientX-dragX,dy=e.clientY-dragY;'\n"
     "        'if(Math.abs(dx)>3||Math.abs(dy)>3)dragMoved=true;'\n"
     "        'stage.scrollLeft=dragSL-dx;stage.scrollTop=dragST-dy;});'\n"
     "        'function endDrag(e){if(!dragging)return;dragging=false;'\n"
     "        'lbImg.classList.remove(\"dragging\");'\n"
     "        'try{lbImg.releasePointerCapture(e.pointerId);}catch(_){}'\n"
     "        'setTimeout(()=>{dragMoved=false;},0);}'\n"
     "        'lbImg.addEventListener(\"pointerup\",endDrag);'\n"
     "        'lbImg.addEventListener(\"pointercancel\",endDrag);'\n"
     # 拖过之后不要再触发"切 1:1"：click 在 pointerup 之后立刻触发，
     # 而 dragMoved 要到 setTimeout(0) 才清零，所以这里能正确判到
     "        'lbImg.addEventListener(\"click\",()=>{if(dragMoved)return;'\n"
     "        'anchor=null;zoomTo(zfTarget>1.001?1:oneToOne(),null);});'"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
