"""量蒙版路径三个表单字段各占多少字节。

动机（实测）：带 --mask 时 1536×1024 发送 2.15 MiB → HTTP 400 被拒；
而 pipeline-notes 记着「mask 表单字段被静默忽略」——若属实，它是纯浪费。
砍掉它能否把 1536×1024 拉回 1.96 MiB 上限内？这里给出数字。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "style-distill" / "round_lib", ROOT / "compose" / "images"):
    sys.path.insert(0, str(p))

from run_round import build_with_mask, G          # noqa: E402

content = Image.open(ROOT / "style-distill/round_snow/input/C_snow_169.png").convert("RGB")
mask = ROOT / "style-distill/round_snow/work/mask_ornament.png"

for tw, th in ((1024, 1024), (1536, 1024), (2048, 1152)):
    files, cov = build_with_mask(content, mask, tw, th, "crop", [], invert=False)
    print(f"\n=== 目标 {tw}x{th}　可改面积 {cov:.1f}% ===")
    tot = 0
    for k, v in files.items():
        n = len(v[1])
        tot += n
        print(f"    {k:10s} {v[0]:14s} {n:9,d} B  {n/1048576:5.2f} MiB")
    print(f"    {'合计':10s} {'':14s} {tot:9,d} B  {tot/1048576:5.2f} MiB")
    for drop in ("mask",):
        if drop in files:
            rest = tot - len(files[drop][1])
            verdict = "✓ 落入上限内" if rest < 1.96 * 1048576 else "✗ 仍超"
            print(f"    → 去掉 {drop} 字段后 {rest:,d} B = {rest/1048576:.2f} MiB  {verdict}")
