"""把画廊页里的 <script> 抽出来交给 node --check 做语法校验。

灯箱全靠这段 JS；语法错一次就整块失效，而我在浏览器里点不了，所以用 node 先验语法。
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

page = urllib.request.urlopen("http://127.0.0.1:8000/gallery", timeout=30).read().decode("utf-8", "replace")
blocks = re.findall(r"<script>(.*?)</script>", page, re.S)
print(f"  页内 <script> 块：{len(blocks)} 个，共 {sum(len(b) for b in blocks)} 字")

ok = True
for i, js in enumerate(blocks, 1):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / f"page{i}.js"
        f.write_text(js, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    print(f"  第 {i} 块 node --check → exit={r.returncode}")
    if r.returncode != 0:
        ok = False
        print("    " + (r.stderr or "").strip().splitlines()[0][:200] if r.stderr else "")
    else:
        print("    ✓ 语法通过")
print("  → " + ("全部通过" if ok else "有语法错误，必须修"))
sys.exit(0 if ok else 1)
