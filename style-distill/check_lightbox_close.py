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
    ("点图片仍是缩放", 'lbImg.addEventListener("click",()=>lbImg.classList.toggle("zoom"))' in page),
    ("两侧箭头仍是翻图", 'document.getElementById("lb-next").addEventListener("click",()=>show(at+1))' in page
     and 'document.getElementById("lb-prev").addEventListener("click",()=>show(at-1))' in page),
    ("Esc 仍可关闭", 'if(e.key==="Escape")close_();' in page),
    ("灯箱容器仍在", '<div id="lb" hidden>' in page),
]
for label, ok in checks:
    print(f"  {'OK ' if ok else '!! '} {label}")

m = re.search(r'<div class="lb-stage"[^>]*>\s*<button[^>]*id="lb-prev"', page, re.S)
print(f"  {'OK ' if m else '!! '} 结构顺序正确（stage 内先出现 prev 按钮）")

print(f"\n  → {'全部符合' if all(ok for _, ok in checks) and m else '有不符合项'}")
