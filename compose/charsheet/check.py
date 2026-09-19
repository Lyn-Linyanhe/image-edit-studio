"""Where did the render actually change? Objective check for "style only" edits.

Usage: python check.py <source> <result> [out-prefix]

Reports:
  - global mean absolute difference
  - the share of pixels essentially unchanged (<8) and strongly changed (>24)
  - a row-by-row change profile, so a shifted figure shows up as a band
  - writes <prefix>_diff.png (heat map) and <prefix>_side.png (source | result | diff)
"""
import sys

import numpy as np
from PIL import Image

src, res = sys.argv[1], sys.argv[2]
prefix = sys.argv[3] if len(sys.argv) > 3 else "check"

A = Image.open(src).convert("RGB")
B = Image.open(res).convert("RGB")
print(f"source {A.size}   result {B.size}")


def fit_to(img, size):
    """Crop-to-fill, the same way normalise_to_size(..., 'crop') does.

    Stretching instead would inflate every difference and could fake a
    'the figure moved' verdict, so the aspect ratio is never distorted here.
    """
    tw, th = size
    sa, ta = img.width / img.height, tw / th
    if abs(sa - ta) < 0.01:
        return img.resize(size, Image.LANCZOS)
    if sa > ta:
        nw = int(img.height * ta)
        ox = (img.width - nw) // 2
        return img.crop((ox, 0, ox + nw, img.height)).resize(size, Image.LANCZOS)
    nh = int(img.width / ta)
    oy = (img.height - nh) // 2
    return img.crop((0, oy, img.width, oy + nh)).resize(size, Image.LANCZOS)


if abs(A.width / A.height - B.width / B.height) > 0.01:
    print(f"NOTE aspect differs ({A.width / A.height:.3f} vs {B.width / B.height:.3f}); "
          "source is crop-to-filled, not stretched")

Aa = np.asarray(fit_to(A, B.size)).astype(float)
Ba = np.asarray(B).astype(float)
diff = np.abs(Aa - Ba).mean(axis=2)

print(f"\nmean abs diff        : {diff.mean():.1f}")
print(f"unchanged (<8)       : {(diff < 8).mean() * 100:.1f}%")
print(f"strongly changed (>24): {(diff > 24).mean() * 100:.1f}%")

# best global shift: if the figure merely MOVED, a small offset will match much better
best = None
for dy in range(-40, 41, 4):
    for dx in range(-40, 41, 4):
        sa = np.roll(np.roll(Aa, dy, axis=0), dx, axis=1)
        d = np.abs(sa - Ba).mean()
        if best is None or d < best[0]:
            best = (d, dx, dy)
print(f"best global shift    : dx={best[1]:+d} dy={best[2]:+d} -> diff {best[0]:.1f}")
if best[0] < diff.mean() - 3:
    print("  >>> the result matches better when SHIFTED: the figure MOVED, "
          "this is not a style-only edit")
else:
    print("  >>> no meaningful shift helps: the figure stayed put")


def band(name, arr):
    print(f"{name:9s} " + "".join(" .:-=+*#%@"[min(9, int(arr[i:i + 10].mean() / 10))]
                                  for i in range(0, len(arr) - 9, 10)))


band("rows", diff.mean(axis=1))
band("cols", diff.mean(axis=0))
print("          scale: ' '=<10  '@'=90+   (per 10-pixel band)")

# images
hm = np.clip(diff / 60 * 255, 0, 255).astype(np.uint8)
Image.fromarray(hm, "L").save(f"{prefix}_diff.png")

w, h = B.size
side = Image.new("RGB", (w * 3 + 20, h), (255, 255, 255))
side.paste(fit_to(A, B.size), (0, 0))
side.paste(B, (w + 10, 0))
side.paste(Image.fromarray(hm, "L").convert("RGB"), (w * 2 + 20, 0))
side.save(f"{prefix}_side.png")
print(f"\nwrote {prefix}_diff.png and {prefix}_side.png")
