"""按目录生成带文件名的审阅拼版，用于**看图核对分类**（不靠文件名猜）。

用法：python make_review_sheet.py <目录> [<目录> ...] --out out.png [--cols 5] [--cell 260]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")

EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

ap = argparse.ArgumentParser()
ap.add_argument("dirs", nargs="+")
ap.add_argument("--out", required=True)
ap.add_argument("--cols", type=int, default=5)
ap.add_argument("--cell", type=int, default=260)
a = ap.parse_args()

files: list[Path] = []
for d in a.dirs:
    p = Path(d)
    if p.is_file():
        files.append(p)
    else:
        files += sorted(q for q in p.rglob("*") if q.suffix.lower() in EXTS)
print(f"  选中 {len(files)} 张")

cell, pad, lab = a.cell, 8, 26
cols = a.cols
rows = (len(files) + cols - 1) // cols
W = cols * (cell + pad) + pad
H = rows * (cell + lab + pad) + pad
sheet = Image.new("RGB", (W, H), (18, 20, 24))
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    r, c = divmod(i, cols)
    x = pad + c * (cell + pad)
    y = pad + r * (cell + lab + pad)
    try:
        im = Image.open(f).convert("RGB")
    except Exception as e:
        dr.text((x + 4, y + 4), f"打不开 {e.__class__.__name__}", fill=(255, 120, 120))
        continue
    im.thumbnail((cell, cell), Image.LANCZOS)
    ox = x + (cell - im.width) // 2
    oy = y + (cell - im.height) // 2
    sheet.paste(im, (ox, oy))
    dr.rectangle([x, y, x + cell, y + cell], outline=(60, 66, 76))
    name = f.name if len(f.name) <= 34 else f.name[:31] + "…"
    dr.text((x + 3, y + cell + 6), name, fill=(210, 216, 224))
    dr.text((x + 3, y + cell + 15), f.parent.name, fill=(140, 150, 165))

out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out)
print(f"  写出 {out}  {sheet.size}  {out.stat().st_size // 1024} KB")
