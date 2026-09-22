"""验收"只从本轮计入、之前全部隐藏"：页面上不得出现任何更早轮次的路径。"""
from __future__ import annotations

import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
page = urllib.request.urlopen("http://127.0.0.1:8000/gallery", timeout=30).read().decode("utf-8", "replace")

cards = re.findall(r'<figure class="card" data-cat="(\w+)">.*?data-file="([^"]+)"', page, re.S)
print(f"  卡片 {len(cards)} 张：")
from collections import Counter                                     # noqa: E402
print("   分类计数：", dict(Counter(c for c, _ in cards)))
rels = [f.split("mantu")[-1].lstrip("\\/").replace("\\", "/") for _, f in cards]
for r in sorted(rels):
    print(f"     {r}")

bad = [r for r in rels if not r.startswith("style-distill/round_arcade/")]
print(f"\n  属于本轮 (round_arcade) 的：{len(rels) - len(bad)} / {len(rels)}")
print(f"  不该出现的（更早轮次等）：{bad if bad else '无 ✓'}")

for token in ("round_manga", "round_snow", "target_t2", "ref_xiami", "compose/"):
    print(f"  页面里出现 '{token}'：{token in page}")

print(f"\n  还有范围开关吗（应为 False）：{'data-scope' in page}")
m = re.search(r'id="hint">(.*?)</span>', page, re.S)
print("  页头：\n   ", (m.group(1) if m else "?")[:200])
