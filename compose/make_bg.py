"""Generate the 灰绿 background, matching the ORIGINAL's measured structure.

Measured from base_v1 (837x1243):
  col bands 0..11 means:  129.5 150.6 150.3 148.8 143.5 143.7 136.0 126.3 116.7 99.6 88.8 81.2
  row bands 0..11 means:  126.2 133.7 124.4 123.5 124.9 138.4 131.1 117.8 130.2 144.4 120.0 100.1
  top-center (418,8)   = 155,156,149   -> brightest zone, cool/neutral
  top-right corner     =  73, 75, 67   -> far right is darkest
  right-mid            =  75, 74, 65
  left-mid             = 136,143,154   -> slightly BLUE on the left edge
  bottom-left          = 106,106,106   -> neutral gray
  bottom-center        =  94, 95, 92

So: strong left->right luminance falloff (~150 -> ~81), plus a top-middle
light pocket, and a slightly blue cast along the left edge.

Output is a smooth, NOISE-FREE gradient (no brush texture, no cloud/雾纹),
built from the percentile-filtered column/row profiles and lightly smoothed.
"""
import numpy as np
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
from PIL import Image, ImageFilter

BASE = f"{_MANTU_ROOT_STR}/compose/"
OUT = BASE + "bg_graygreen.png"

im = Image.open(BASE + "base_v1.png").convert("RGB")
a = np.asarray(im).astype(np.float32)
h, w, _ = a.shape

# --- Column profile: use the TOP band only (y<15%) because the figure sits in
# the middle/lower area and would otherwise contaminate the profile.
top = a[: int(h * 0.13)]
col = np.median(top, axis=0)                     # (w,3)

# --- Row profile: use the RIGHT band only (x>88%) which is pure background.
right = a[:, int(w * 0.88):]
row = np.median(right, axis=1)                   # (h,3)

# Blend the two profiles into a separable-ish field, then smooth hard so no
# brush strokes or noise survive.
col_img = np.tile(col[None, :, :], (h, 1, 1))
row_img = np.tile(row[:, None, :], (1, w, 1))
field = 0.6 * col_img + 0.4 * row_img

# floor/ceiling clamp so the figure area never dominates the estimate
lo = np.percentile(field.reshape(-1, 3), 2, axis=0)
hi = np.percentile(field.reshape(-1, 3), 98, axis=0)
field = np.clip(field, lo, hi)

bg = Image.fromarray(np.clip(field, 0, 255).astype(np.uint8), "RGB")

# heavy blur => guaranteed smooth gradient, no texture
bg = bg.filter(ImageFilter.GaussianBlur(radius=max(w, h) * 0.035))

# re-assert the measured extremes that the blur washed out
b = np.asarray(bg).astype(np.float32)
b[:, : int(w * 0.06)] *= 0.97
b[:, -int(w * 0.12):] *= 0.90
bg = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8), "RGB")

bg.save(OUT)
print("saved", OUT, bg.size)

c = np.asarray(bg).astype(np.float32)
print("col means:", [round(float(c[:, j*w//12:(j+1)*w//12].mean()), 1) for j in range(12)])
print("row means:", [round(float(c[i*h//12:(i+1)*h//12].mean()), 1) for i in range(12)])
print("corners:",
      c[10, 10].round(1), c[10, -10].round(1),
      c[-10, 10].round(1), c[-10, -10].round(1))
