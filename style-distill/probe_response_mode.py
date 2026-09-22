"""把台账里的 url / b64 两种响应模式与实际输出尺寸对起来。

动机：台账（R1）刚上线就抓到一条**以前零痕迹**的路径——b64 响应。
怀疑"输出尺寸不受控（1254×1254）"与响应模式有关，而不是与蒙版有关。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

rows = [json.loads(x) for x in
        (Path(__file__).resolve().parent / "round_lib" / "call_ledger.jsonl")
        .read_text(encoding="utf-8").strip().splitlines() if x.strip()]

print(f"  台账 {len(rows)} 条；以下是实际发出的请求：\n")
for r in rows:
    if r.get("result") not in ("url", "b64"):
        continue
    out = Path(r["out"])
    try:
        size = Image.open(out).size
    except Exception:
        size = "(读不到)"
    print(f"  {r['ts']}  {r['result']:5s}  请求 {r['size']:10s} 实得 {str(size):14s} "
          f"表单项={r.get('fields')}  输出 {r.get('out_bytes')} B")
    print(f"      掩膜 invert={r.get('mask_invert')} coverage={r.get('coverage_pct')}")
