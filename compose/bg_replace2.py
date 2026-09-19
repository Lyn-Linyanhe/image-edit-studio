"""Background-only replacement, v2.

Fixes over v1:
  - NO convex hull (it inflated the mask 45% -> 57%)
  - fill the mask's interior holes by contour RETR_CCOMP instead of flood fill
  - build the background as blur-then-inpaint (smooth, no streaks)
  - NO global percentile remap (that destroyed the left->right falloff and
    introduced the blue cast); only a gentle chroma pull to the target 灰绿
  - narrow blend band so the new background keeps a real gradient
"""
import os
import cv2
import numpy as np

BASE = "C:/Users/typ/Desktop/mantu/compose/"
OUT = BASE + "out2/"
os.makedirs(OUT, exist_ok=True)

bgr = cv2.imread(BASE + "base_v1.png", cv2.IMREAD_COLOR)
h, w = bgr.shape[:2]

# ---- figure mask ----------------------------------------------------------
mask = np.zeros((h, w), np.uint8)
rect = (int(w * 0.06), int(h * 0.02), int(w * 0.92), int(h * 0.96))
cv2.grabCut(bgr, mask, rect, np.zeros((1, 65), np.float64),
            np.zeros((1, 65), np.float64), 6, cv2.GC_INIT_WITH_RECT)
m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)

num, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
if num > 1:
    m = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)

k = max(3, int(min(w, h) * 0.014))
k += (k + 1) % 2
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)), iterations=2)

# fill interior holes via external-contour fill (catches neck/chest islands)
cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
filled = np.zeros((h, w), np.uint8)
cv2.drawContours(filled, cnts, -1, 1, thickness=cv2.FILLED)
print(f"mask solid %: {filled.mean()*100:.1f}")

# ---- background: blur first, then inpaint the hole ------------------------
sig = min(w, h) * 0.055
smooth = cv2.GaussianBlur(bgr, (0, 0), sig)
hole = (filled * 255).astype(np.uint8)
bg_new = cv2.inpaint(smooth, hole, 5, cv2.INPAINT_TELEA)
bg_new = cv2.GaussianBlur(bg_new, (0, 0), min(w, h) * 0.030)

# ---- gentle chroma pull toward 灰绿 (preserves luminance structure) -------
# original background chroma sample: neutral-olive, B slightly below R/G.
bf = bg_new.astype(np.float32)
lum = bf @ np.array([0.114, 0.587, 0.299], np.float32)      # BGR->Y
tgt = np.stack([lum * 0.985, lut_g := lum * 1.005, lum * 1.015], axis=-1)  # B,G,R
bf = 0.55 * bf + 0.45 * tgt
bg_new = np.clip(bf, 0, 255).astype(np.uint8)

# ---- feathered blend ------------------------------------------------------
margin = int(min(w, h) * 0.014)
zone = cv2.dilate(filled, cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE, (margin * 2 + 1, margin * 2 + 1)))
band = max(6, int(min(w, h) * 0.011))
feather = cv2.GaussianBlur(zone.astype(np.float32), (0, 0), band * 0.5)
feather = np.clip(feather * 1.8, 0, 1)
feather[filled > 0] = 1.0            # figure itself never receives new bg

mix = (bgr.astype(np.float32) * feather[..., None]
       + bg_new.astype(np.float32) * (1 - feather[..., None]))
mix = np.clip(mix, 0, 255).astype(np.uint8)

prot = filled > 0
print("figure pixels bit-identical:",
      np.array_equal(mix[prot], bgr[prot]))
print(f"new-background area: {(1-filled.mean())*100:.1f}%")

cv2.imwrite(OUT + "01_bg_only.png", bg_new)
cv2.imwrite(OUT + "02_result.png", mix)

c = cv2.cvtColor(mix, cv2.COLOR_BGR2RGB).astype(np.float32)
print("col means:", [round(float(c[:, j*w//12:(j+1)*w//12].mean()), 1) for j in range(12)])
print("row means:", [round(float(c[i*h//12:(i+1)*h//12].mean()), 1) for i in range(12)])
for kk, (x, y) in {"TL": (10, 10), "TR": (w-10, 10), "BL": (10, h-10),
                   "BR": (w-10, h-10), "Lmid": (10, h//2),
                   "Rmid": (w-10, h//2), "Tmid": (w//2, 8)}.items():
    print(f"  {kk}: {c[y, x].round(1)}")
