"""Ruler overlays: burn a labelled coordinate grid onto a region so positions can be
read off directly instead of estimated.

Usage: python ruler.py <source-image> <x0> <y0> <x1> <y1> <out-name> [grid-step-px]
Coordinates are in ORIGINAL image pixels; labels are given in full-image fractions.
"""
import sys

from PIL import Image, ImageDraw

src, X0, Y0, X1, Y1, name = sys.argv[1:7]
X0, Y0, X1, Y1 = int(X0), int(Y0), int(X1), int(Y1)
step = int(sys.argv[7]) if len(sys.argv) > 7 else 50

img = Image.open(src).convert("RGB")
W, H = img.size
crop = img.crop((X0, Y0, X1, Y1))
scale = max(1, round(1000 / max(crop.width, crop.height)))
crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
d = ImageDraw.Draw(crop)

for x in range(X0 - X0 % step + step, X1, step):
    px = (x - X0) * scale
    d.line([(px, 0), (px, crop.height)], fill=(255, 0, 0), width=1)
    d.text((px + 2, 2), f"{x / W:.2f}", fill=(255, 0, 0))
for y in range(Y0 - Y0 % step + step, Y1, step):
    py = (y - Y0) * scale
    d.line([(0, py), (crop.width, py)], fill=(255, 0, 0), width=1)
    d.text((2, py + 2), f"{y / H:.2f}", fill=(255, 0, 0))

crop.save(name)
print(f"{name}  crop=({X0},{Y0})-({X1},{Y1})  scale={scale}x  labels=full-image fractions")
