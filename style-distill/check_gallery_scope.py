"""验收"默认只看本轮"：页签/范围按钮、默认可见卡片数、切到全部历史的数量、JS 语法。"""
from __future__ import annotations

import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
page = urllib.request.urlopen("http://127.0.0.1:8000/gallery", timeout=30).read().decode("utf-8", "replace")

print("  范围按钮：")
for m in re.finditer(r'data-scope="(latest|all)">([^<]*)<span class="n">(\d+)</span>', page):
    print(f"     {m.group(2).strip():8s} → {m.group(3)} 张")

print("\n  卡片按 scope 计数：")
for sc in ("latest", "older"):
    n = len(re.findall(r'<figure class="card" data-cat="\w+" data-scope="' + sc + r'">', page))
    print(f"     {sc:8s} {n} 张")

print("\n  本轮卡片明细（rel 从 data-file 里取）：")
for m in re.finditer(r'data-cat="(\w+)" data-scope="latest"', page):
    pass
rows = re.findall(r'<figure class="card" data-cat="(\w+)" data-scope="latest">.*?data-file="([^"]+)"', page, re.S)
for cat, f in rows:
    rel = f.split("mantu")[-1].lstrip("\\/").replace("\\", "/")
    print(f"     [{cat:9s}] {rel}")

m = re.search(r'id="hint">(.*?)</span>', page, re.S)
print("\n  页头说明：\n   ", (m.group(1) if m else "?")[:220])
print(f"\n  默认 scope 是 latest：{'let cat=\"all\",scope=\"latest\"' in page}")
