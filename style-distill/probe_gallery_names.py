"""逐目录列出图片真名目，找出"按路径分类"最可能分错的地方。

只列名与尺寸，不下结论；把需要看图才能判的目录标出来。
"""
from __future__ import annotations
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))

import os
import sys
from collections import defaultdict

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

ROOTS = [rf"{_MANTU_ROOT_STR}\style-distill", rf"{_MANTU_ROOT_STR}\compose"]
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
BASE = _MANTU_ROOT_STR

bydir = defaultdict(list)
for root in ROOTS:
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
        for f in fn:
            if os.path.splitext(f)[1].lower() in EXTS:
                p = os.path.join(dp, f)
                rel_dir = os.path.relpath(dp, BASE).replace("\\", "/")
                try:
                    sz = Image.open(p).size
                except Exception:
                    sz = "?"
                bydir[rel_dir].append((f, sz))

for d in sorted(bydir, key=lambda k: -len(bydir[k])):
    items = bydir[d]
    print(f"\n== {d}  ({len(items)} 张) ==")
    for f, sz in sorted(items):
        print(f"   {f:44s} {sz}")
