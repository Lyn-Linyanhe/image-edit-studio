"""Background-only replacement, v3 (final).

Problem in v2: the blend band was centred on the mask boundary, so where the
mask already overshot the figure the new background ate real character pixels,
and where it undershot, original background survived as pale blade-shaped
notches around the head.

Fix: make the blend asymmetric. The mask is TIGHTENED (eroded) first so the
surrounding hair tips belong to the protected side, then the transition is
expanded OUTWARD only. The result is a soft vignette-like falloff instead of a
ring pinned to the silhouette.
"""
import os
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
import cv2
import numpy as np

BASE = f"{_MANTU_ROOT_STR}/compose/"
OUT = BASE + "final/"
os.makedirs(OUT, exist_ok=True)

bgr = cv2.imread(BASE + "base_v1.png", cv2.IMREAD_COLOR)
h, w = bgr.shape[:2]

# ---------- figure mask ----------
mask = np.zeros((h, w), np.uint8)
rect = (int(w * 0.06), int(h * 0.02), int(w * 0.92), int(h * 0.96))
cv2.grabCut(bgr, mask, rect, np.zeros((1, 65), np.float64),
            np.zeros((1, 65), np.float64), 6, cv2.GC_INIT_WITH_RECT)
m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
num, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
if num > 1:
    m = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)

k = max(3, int(min(w, h) * 0.014)); k += (k + 1) % 2
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)), iterations=2)
cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
solid = np.zeros((h, w), np.uint8)
cv2.drawContours(solid, cnts, -1, 1, thickness=cv2.FILLED)

# ---------- background ----------
sig = min(w, h) * 0.055
smooth = cv2.GaussianBlur(bgr, (0, 0), sig)
bg_new = cv2.inpaint(smooth, (solid * 255).astype(np.uint8), 5, cv2.INPAINT_TELEA)
bg_new = cv2.GaussianBlur(bg_new, (0, 0), min(w, h) * 0.030)

bf = bg_new.astype(np.float32)
lum = bf @ np.array([0.114, 0.587, 0.299], np.float32)
tgt = np.stack([lum * 0.985, lum * 1.005, lum * 1.015], axis=-1)
bg_new = np.clip(0.55 * bf + 0.45 * tgt, 0, 255).astype(np.uint8)

# ---------- asymmetric blend ----------
# 1) TIGHTEN: pull the mask in so hair tips stay protected
tight = cv2.erode(solid, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
# 2) grow only outward, far enough that the transition never shows a rim
grow = int(min(w, h) * 0.045)
outer = cv2.dilate(tight, cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1)))
# 3) feather from tight -> outer, using a distance-based ramp for a clean,
#    monotonic falloff (no ringing)
dist = cv2.distanceTransform((1 - tight).astype(np.uint8), cv2.DIST_L2, 5)
ramp = np.clip((outer - 0).astype(np.float32), 0, 1)          # 0/1 outer region
t = np.clip(dist / float(grow), 0, 1)                          # 0 at figure
feather = np.where(outer > 0, np.clip(1.0 - t, 0, 1), 0.0).astype(np.float32)
feather[tight > 0] = 1.0
# smooth the ramp so no contour steps appear
feather = cv2.GaussianBlur(feather, (0, 0), grow * 0.20)
feather = np.clip((feather - 0.02) / 0.96, 0, 1)
feather[solid > 0] = 1.0   # the figure proper is fully protected

mix = (bgr.astype(np.float32) * feather[..., None]
       + bg_new.astype(np.float32) * (1 - feather[..., None]))
mix = np.clip(mix, 0, 255).astype(np.uint8)

prot = solid > 0
print("figure pixels bit-identical:", np.array_equal(mix[prot], bgr[prot]))
print(f"figure {solid.mean()*100:.1f}%   full-protect {feather.mean()*100:.1f}%")

cv2.imwrite(OUT + "result_bg.png", bg_new)
cv2.imwrite(OUT + "result.png", mix)
# mask overlay for inspection
ov = bgr.copy()
ov[outer == 0] = (255, 255, 255)
ov[(outer > 0) & (solid == 0)] = (0, 255, 255)
cv2.imwrite(OUT + "mask_preview.png", ov)

c = cv2.cvtColor(mix, cv2.COLOR_BGR2RGB).astype(np.float32)
print("col means:", [round(float(c[:, j*w//12:(j+1)*w//12].mean()), 1) for j in range(12)])
for kk, (x, y) in {"TL": (10, 10), "TR": (w-10, 10), "BL": (10, h-10),
                   "BR": (w-10, h-10), "Lmid": (10, h//2),
                   "Rmid": (w-10, h//2), "Tmid": (w//2, 8)}.items():
    print(f"  {kk}: {c[y, x].round(1)}")
