"""确认页头那句"输入口径"说明真的渲染出来了，且卡片数/页签一致。"""
from __future__ import annotations

import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
page = urllib.request.urlopen("http://127.0.0.1:8000/gallery", timeout=30).read().decode("utf-8", "replace")

m = re.search(r'id="hint">(.*?)</span>', page, re.S)
print("  页头说明：")
print("   ", (m.group(1) if m else "（没找到）")[:300])

for key, label in (("input", "输入"), ("reference", "参考"), ("deliver", "成果")):
    n = len(re.findall(r'<figure class="card" data-cat="' + key + r'">', page))
    print(f"  卡片 {label}：{n}")

print(f"  含'只计入最近一次上传'：{'只计入最近一次上传' in page}")
