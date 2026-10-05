"""找出"参考图"候选：input/、ref_*/、references/、pose_ref*/ 下的图，以及名字里带 ref 的。

先出数再定规则——上一轮就是靠这个才发现 round_lib、_smoke 之类会被误判。
"""
from __future__ import annotations
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOTS = [rf"{_MANTU_ROOT_STR}\style-distill", rf"{_MANTU_ROOT_STR}\compose"]
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
BASE = _MANTU_ROOT_STR

cand = []
for root in ROOTS:
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
        rel_dir = os.path.relpath(dp, BASE).replace("\\", "/")
        segs = rel_dir.split("/")
        dirish = (any(s.startswith("ref") or s == "references" or s.startswith("pose_ref") for s in segs)
                  or rel_dir.endswith("/input"))
        for f in fn:
            if os.path.splitext(f)[1].lower() not in EXTS:
                continue
            name = f.lower()
            if dirish or "ref" in name:
                cand.append((rel_dir, f, "目录特征" if dirish else "名字带 ref"))

print(f"  疑似参考图/输入图 {len(cand)} 张：\n")
for rel_dir, f, why in sorted(cand):
    print(f"   {rel_dir:46s} {f:34s} {why}")

print("\n  目录归纳：")
from collections import Counter                                     # noqa: E402
for d, n in Counter(d for d, _, _ in cand).most_common():
    print(f"   {n:3d}  {d}")
