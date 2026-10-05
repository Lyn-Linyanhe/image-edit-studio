"""把 build_with_mask 真正生成的 image[1]（涂红视觉蒙版）落盘看一眼。

这是"模型实际收到的标记图"，比任何推测都直接。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "style-distill" / "round_lib", ROOT / "compose" / "images"):
    sys.path.insert(0, str(p))

from run_round import build_with_mask          # noqa: E402

content = Image.open(ROOT / "style-distill/round_snow/input/C_snow_169.png").convert("RGB")
mask = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "style-distill/round_snow/work/mask_ornament.png"
tag = mask.stem
print(f"  蒙版：{mask}")

files, cov = build_with_mask(content, mask, 1024, 1024, "crop", [], invert=False)
NAMES = {"image": "content", "image[1]": "redmark", "mask": "alpha"}
for k in ("image", "image[1]", "mask"):
    if k in files:
        data = files[k][1]
        p = ROOT / "style-distill/round_snow/work" / f"_sent_{tag}_{NAMES[k]}.png"
        p.write_bytes(data)
        im = Image.open(p)
        print(f"  {k:10s} -> {p.name}  {im.size}  {len(data):,} B   mode={im.mode}")
print(f"  可改面积 {cov:.2f}%")

# 缩到 512 便于查看
big = ROOT / "style-distill/round_snow/work" / f"_sent_{tag}_redmark.png"
small = ROOT / "style-distill/round_snow/work" / f"_sent_{tag}_redmark_small.png"
Image.open(big).resize((512, 512), Image.LANCZOS).save(small)
print(f"  已另存 {small.name} (512×512)")
