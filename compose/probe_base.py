"""Probe the original reference: where is the figure, where is the background?

Prints a coarse luminance map so we can see the layout before choosing
GrabCut seeds. Also clusters border pixels to learn the local background
colour(s) -- the original bg is NOT flat (there are diagonal architectural
shapes), which matters for edge alpha estimation later.
"""
import numpy as np
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
from PIL import Image

BASE = f"{_MANTU_ROOT_STR}/compose/"
im = Image.open(BASE + "base_v1.png").convert("RGB")
a = np.asarray(im).astype(np.float32)
h, w, _ = a.shape
print(f"size {w}x{h}  ratio {w/h:.4f}")

g = a.mean(axis=2)

# 24x32 coarse luminance grid, rendered as characters
gy, gx = 24, 32
print("\ncoarse luminance map (dark=# , light=' '):")
ramp = " .:-=+*#%@"
for i in range(gy):
    y0, y1 = i * h // gy, (i + 1) * h // gy
    row = ""
    for j in range(gx):
        x0, x1 = j * w // gx, (j + 1) * w // gx
        v = g[y0:y1, x0:x1].mean()
        row += ramp[min(len(ramp) - 1, int((255 - v) / 256 * len(ramp)))]
    print("   " + row)

# column/row luminance profiles (coarse)
print("\nrow means (top->bottom), 12 bands:")
for i in range(12):
    y0, y1 = i * h // 12, (i + 1) * h // 12
    b = a[y0:y1]
    print(f"   band{i:2d} y{y0:4d}-{y1:4d}  {b.reshape(-1,3).mean(axis=0).round(1)}")

print("\ncol means (left->right), 12 bands:")
for j in range(12):
    x0, x1 = j * w // 12, (j + 1) * w // 12
    b = a[:, x0:x1]
    print(f"   band{j:2d} x{x0:4d}-{x1:4d}  {b.reshape(-1,3).mean(axis=0).round(1)}")

# sample specific points likely to be background
pts = {
    "top-left corner": (10, 10),
    "top-center": (w // 2, 8),
    "top-right corner": (w - 10, 10),
    "left-mid": (8, h // 2),
    "right-mid": (w - 8, h // 2),
    "bottom-left": (10, h - 10),
    "bottom-center": (w // 2, h - 8),
    "bottom-right": (w - 10, h - 10),
}
print("\npoint samples (x,y)->RGB:")
for k, (x, y) in pts.items():
    print(f"   {k:18s} ({x:4d},{y:4d}) {a[y, x].round(1)}")
