"""Replace ONLY the background, keeping the figure's pixels untouched.

Key idea: we do NOT try to cut the figure out. We rebuild the background by
inpainting over the figure, then blend the new background into the original
image through a feathered mask that lies OUTSIDE the figure.

Because the original figure has no hard edge against its background (soft,
semi-transparent hair over a low-contrast gradient), a blend band a few dozen
pixels wide is visually invisible, while every pixel inside the protected zone
stays bit-for-bit original.

Steps:
  1. load base_v1
  2. build a figure mask (grabcut + largest comp + close + hole fill)
  3. dilate it -> "protected zone" (figure + margin). Nothing inside changes.
  4. inpaint the background across the protected zone (TELEA)
  5. de-tint the inpainted background to the target 灰绿 target tone
  6. feather-blend inpainted bg into the original outside the protected zone
"""
import cv2
import numpy as np
from PIL import Image

BASE = "C:/Users/typ/Desktop/mantu/compose/"
OUT = BASE + "out/"

import os
os.makedirs(OUT, exist_ok=True)

bgr = cv2.imread(BASE + "base_v1.png", cv2.IMREAD_COLOR)
h, w = bgr.shape[:2]

# ---- 1. figure mask -------------------------------------------------------
mask = np.zeros((h, w), np.uint8)
rect = (int(w * 0.06), int(h * 0.02), int(w * 0.92), int(h * 0.96))
bgd = np.zeros((1, 65), np.float64)
fgd = np.zeros((1, 65), np.float64)
cv2.grabCut(bgr, mask, rect, bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)

num, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
if num > 1:
    m = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)

k = max(3, int(min(w, h) * 0.012))
k += (k + 1) % 2
ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, ker, iterations=2)

# fill holes (the neck/chest ellipse) aggressively AND convex-ify the hull so
# no interior "background island" survives inside the figure
ff = m.copy()
cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
m = np.clip(m + (ff == 0).astype(np.uint8), 0, 1).astype(np.uint8)

pts = cv2.findNonZero(m)
hull = cv2.convexHull(pts)
hull_m = np.zeros((h, w), np.uint8)
cv2.fillConvexPoly(hull_m, hull, 1)
# union: mask OR hull covers interior islands; hull alone would be too fat at
# the concave parts, so use mask + hull-interior-only (keep mask's outer shape)
m = np.clip(m + (hull_m & 1), 0, 1).astype(np.uint8)

# ---- 2. protected zone: figure + margin ----------------------------------
margin = int(min(w, h) * 0.030)
kz = margin * 2 + 1
zone = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kz, kz)))
print(f"figure {m.mean()*100:.1f}%  protected zone {zone.mean()*100:.1f}%  margin {margin}px")

# ---- 3. inpaint background across the protected zone ---------------------
inpaint_mask = (zone * 255).astype(np.uint8)
bg_new = cv2.inpaint(bgr, inpaint_mask, 7, cv2.INPAINT_TELEA)
# the result is very smooth already; blur a touch to kill inpaint streaks
bg_new = cv2.GaussianBlur(bg_new, (0, 0), max(2.0, min(w, h) * 0.012))

# ---- 4. re-tint to the measured 灰绿 target -----------------------------
# measured original background-ish extremes (right edge dark, upper-middle light)
bgf = bg_new.astype(np.float32)
lo = np.percentile(bgf.reshape(-1, 3), 3, axis=0)
hi = np.percentile(bgf.reshape(-1, 3), 97, axis=0)
bgf = np.clip((bgf - lo) / np.maximum(hi - lo, 1.0), 0, 1)
# target range: dark ~ (74,75,67) warm-olive, light ~ (152,152,143)
tgt_lo = np.array([74.0, 75.0, 67.0])
tgt_hi = np.array([152.0, 152.0, 143.0])
bgf = bgf * (tgt_hi - tgt_lo) + tgt_lo
bg_new = np.clip(bgf, 0, 255).astype(np.uint8)

# ---- 5. feathered blend ---------------------------------------------------
# soft zone edge: 1 inside the protected zone, ramping to 0 outside over `band`
band = max(8, int(min(w, h) * 0.020))
feather = cv2.GaussianBlur(zone.astype(np.float32), (0, 0), band * 0.5)
feather = np.clip(feather * 1.6, 0, 1)
# hard-protect the core so original pixels are exact there
core = cv2.erode(zone, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
feather[core > 0] = 1.0
# never let the new background into the figure itself
feather[m > 0] = 1.0

mix = (bgr.astype(np.float32) * feather[..., None]
       + bg_new.astype(np.float32) * (1 - feather[..., None]))
mix = np.clip(mix, 0, 255).astype(np.uint8)

# ---- 6. verify: figure pixels are bit-identical --------------------------
prot = (m > 0)
identical = np.array_equal(mix[prot], bgr[prot])
print("figure pixels bit-identical:", identical)

cv2.imwrite(OUT + "01_bg_only.png", bg_new)
cv2.imwrite(OUT + "02_result.png", mix)

# diagnostics
rgb = cv2.cvtColor(mix, cv2.COLOR_BGR2RGB)
Image.fromarray(rgb).save(OUT + "03_result_rgb.png")

c = rgb.astype(np.float32)
print("col means:", [round(float(c[:, j*w//12:(j+1)*w//12].mean()), 1) for j in range(12)])
print("row means:", [round(float(c[i*h//12:(i+1)*h//12].mean()), 1) for i in range(12)])
for kk, (x, y) in {"TL": (10, 10), "TR": (w-10, 10), "BL": (10, h-10),
                   "BR": (w-10, h-10), "BL-mid": (10, h//2)}.items():
    print(f"  {kk}: {c[y, x].round(1)}")
