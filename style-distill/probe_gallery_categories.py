"""先看真实分布，再定分类规则（避免分出空桶或把整类塞错）。

扫描画廊的两个根目录，按"路径特征"试分类并打印每桶数量与样例。
"""
from __future__ import annotations
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))

import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

ROOTS = [rf"{_MANTU_ROOT_STR}\style-distill", rf"{_MANTU_ROOT_STR}\compose"]
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
BASE = _MANTU_ROOT_STR


def scan():
    out = []
    for root in ROOTS:
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
            for f in fn:
                if os.path.splitext(f)[1].lower() in EXTS:
                    p = os.path.join(dp, f)
                    try:
                        out.append((os.stat(p).st_mtime, p))
                    except OSError:
                        pass
    out.sort(reverse=True)
    return out


files = scan()
print(f"  两个根目录下共 {len(files)} 张图（画廊上限 240）\n")

# 目录分布：看"桶"该按什么切
dirs = Counter()
for _, p in files:
    rel = os.path.relpath(p, BASE).replace("\\", "/")
    segs = rel.split("/")
    dirs["/".join(segs[:-1])] += 1
print("  按目录计数（前 20）：")
for d, n in dirs.most_common(20):
    print(f"    {n:4d}  {d}")

print("\n  文件名前缀计数（前 16）：")
pref = Counter()
for _, p in files:
    name = os.path.basename(p)
    pref[name.split("_")[0]] += 1
for k, n in pref.most_common(16):
    print(f"    {n:4d}  {k}_…")


def cat(rel: str) -> str:
    name = os.path.basename(rel).lower()
    segs = [s.lower() for s in rel.replace("\\", "/").split("/")]
    dirs_ = segs[:-1]
    # 对照物/细节件 → 局部
    if any(h in name for h in ("redmark", "_zoom_", "_sheet", "contact", "palette", "_crop")):
        return "局部"
    # 交付件 → 成果：round 根层的 out_*，或 compose 的 out/final/deliver 目录
    if name.startswith("out_"):
        if "lab" not in dirs_ and "work" not in dirs_ and any(d.startswith("round_") for d in dirs_):
            return "成果"
        if "out" in dirs_ or "final" in dirs_ or "deliver" in dirs_:
            return "成果"
    if any(d in ("out", "out2", "final", "final2", "deliver") for d in dirs_):
        return "成果"
    return "过程"


buckets = Counter()
samples = {}
for _, p in files:
    rel = os.path.relpath(p, BASE).replace("\\", "/")
    c = cat(rel)
    buckets[c] += 1
    samples.setdefault(c, []).append(rel)

print("\n  试分类结果：")
for c in ("成果", "局部", "过程"):
    print(f"    {c}  {buckets[c]:4d} 张")
    for s in samples.get(c, [])[:5]:
        print(f"        例：{s}")
