"""验收"点空白关闭"：结构上确认新条件已到位、JS 语法通过、刷新后页面确实是新版。"""
from __future__ import annotations

import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
page = urllib.request.urlopen("http://127.0.0.1:8000/gallery", timeout=30).read().decode("utf-8", "replace")

checks = [
    ("点空白关闭：含 lb-stage 判断", 't.id==="lb-stage"' in page),
    ("仍是点 #lb 本体也关闭", "t===lb" in page),
    ("点图片仍是缩放（带拖过抑制，切到真正的 1:1）",
     'lbImg.addEventListener("click",()=>{if(dragMoved)return;' in page
     and "zoomTo(zfTarget>1.001?1:oneToOne(),null);})" in page),
    ("两侧箭头仍是翻图", 'document.getElementById("lb-next").addEventListener("click",()=>show(at+1))' in page
     and 'document.getElementById("lb-prev").addEventListener("click",()=>show(at-1))' in page),
    ("Esc 仍可关闭", 'if(e.key==="Escape")close_();' in page),
    ("灯箱容器仍在", '<div id="lb" hidden>' in page),
    # ---- 滚轮缩放（丝滑版）
    ("滚轮监听存在且非 passive（否则 preventDefault 无效）",
     'stage.addEventListener("wheel"' in page and "passive:false" in page),
    ("步进按位移的指数曲线（不是固定 ×1.15）", "Math.exp(-dy*0.0006)" in page),
    ("deltaMode 归一化（行/页 → 像素）", "if(e.deltaMode===1)dy*=16" in page),
    ("目标倍率与当前倍率分离 + 逐帧缓动", "zfTarget" in page and "requestAnimationFrame(tick)" in page),
    ("缓动收尾（差值小于阈值时精确落位并停止）",
     "Math.abs(zfTarget-zf)<0.002" in page and "zf=zfTarget;paint();rafId=0;return;" in page),
    ("缩放有下限 1x、上限为动态 maxZ()", "Math.max(1,Math.min(maxZ(),f))" in page),
    ("以光标为锚点（逐帧校正滚动位置）",
     "const rx=(stage.scrollLeft+ax)/oldW" in page and "stage.scrollLeft=rx*lbImg.clientWidth-ax" in page),
    # ---- 缩放基准修正（第一下不该比后面快）
    ("缩放基准是'适应窗口'尺寸（fitW），不是原图像素",
     "const base=fitW||lbImg.naturalWidth||oldW;" in page and "(base*zf).toFixed(1)" in page),
    ("图片加载后量一次 fitW", "lbImg.onload=()=>{captureFit();}" in page and "fitW=lbImg.clientWidth;" in page),
    ("倍率按原图像素显示（100% = 1:1）", "Math.round(zf*fitW/nw*100)" in page),
    ("点图切到真正的 1:1（nw/fitW）", "zoomTo(zfTarget>1.001?1:oneToOne(),null)" in page),
    # ---- 放大后可拖动平移
    ("指针事件拖动平移（pointerdown/move/up）",
     'lbImg.addEventListener("pointerdown"' in page and 'lbImg.addEventListener("pointermove"' in page
     and "function endDrag(e)" in page),
    ("拖动时改的是舞台滚动位置", "stage.scrollLeft=dragSL-dx;stage.scrollTop=dragST-dy;" in page),
    ("只在放大状态可拖（适应窗口时忽略）", "if(lb.hidden||zf<=1.001)return;" in page),
    ("用 setPointerCapture（拖出图片范围不断线）", "setPointerCapture(e.pointerId)" in page
     and "releasePointerCapture(e.pointerId)" in page),
    ("拖过之后抑制误触的'切 1:1'", "if(dragMoved)return;" in page and "setTimeout(()=>{dragMoved=false;},0);" in page),
    ("光标 grab/grabbing + 触屏 touch-action", "cursor:grab;touch-action:none" in page
     and "#lb-img.dragging{cursor:grabbing}" in page),
    ("禁掉原生图片拖拽", 'lbImg.addEventListener("dragstart",e=>e.preventDefault());' in page),
    # ---- 放大后四边都要能看到（flex 居中陷阱）
    ("舞台不再用 flex 居中（否则溢出部分滚不到）",
     ".lb-stage{flex:1;position:relative;overflow:auto;display:flex}" in page
     and "align-items:center;justify-content:center" not in page),
    ("居中式样改由子元素 margin:auto 承担", "object-fit:contain;cursor:zoom-in;margin:auto" in page),
    ("上限保证 1:1 够得到", "function maxZ()" in page and "nw/fitW+1" in page),
    ("顶栏有倍率显示", 'id="lb-zoom"' in page and "zoomLabel()" in page),
    ("切图/关闭时重置并取消动画",
     "resetZoom();" in page and "cancelAnimationFrame(rafId)" in page),
    ("放大时放开 max-height（靠 .zoom 类）", 'lbImg.classList.add("zoom")' in page),
]
for label, ok in checks:
    print(f"  {'OK ' if ok else '!! '} {label}")

m = re.search(r'<div class="lb-stage"[^>]*>\s*<button[^>]*id="lb-prev"', page, re.S)
print(f"  {'OK ' if m else '!! '} 结构顺序正确（stage 内先出现 prev 按钮）")

print(f"\n  → {'全部符合' if all(ok for _, ok in checks) and m else '有不符合项'}")
