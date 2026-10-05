"""Extract the figure from base_v1 with GrabCut, then produce diagnostics.

Diagnostics written to ./diag/:
  01_mask.png      raw grabcut mask (white = figure)
  02_mask_soft.png feathered alpha
  03_checker.png   figure over magenta/green checker -> shows edge quality
  04_graybg.png    figure over a FLAT mid gray -> shows any residual bg halo
  05_orig_annot.png original with the mask outline drawn on it

The flat-gray composite is the important one: any leftover original
background shows up immediately as a gray-green ring/halo.
"""
import os
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
import cv2
import numpy as np
from PIL import Image

BASE = f"{_MANTU_ROOT_STR}/compose/"
DIAG = BASE + "diag/"
os.makedirs(DIAG, exist_ok=True)

bgr = cv2.imread(BASE + "base_v1.png", cv2.IMREAD_COLOR)
h, w = bgr.shape[:2]
print("loaded", w, "x", h)

# ---- 1. edge / contour based foreground hint -------------------------------
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
# local contrast: the figure has much more high-frequency detail than the
# smooth background gradient
fine = cv2.absdiff(gray, cv2.GaussianBlur(gray, (0, 0), 4.0))
fine = cv2.normalize(fine, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

# ---- 2. GrabCut -----------------------------------------------------------
mask = np.zeros((h, w), np.uint8)
rect = (int(w * 0.06), int(h * 0.02), int(w * 0.92), int(h * 0.96))
bgd = np.zeros((1, 65), np.float64)
fgd = np.zeros((1, 65), np.float64)

cv2.grabCut(bgr, mask, rect, bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
print("grabcut fg pixels:", int(m.sum()), f"({m.mean()*100:.1f}%)")

# ---- 3. keep the largest connected component + fill holes ------------------
num, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
if num > 1:
    areas = stats[1:, cv2.CC_STAT_AREA]
    keep = 1 + int(np.argmax(areas))
    m = (lab == keep).astype(np.uint8)
    print("largest component area:", int(m.sum()))

# close small notches, then fill enclosed holes
k = max(3, int(min(w, h) * 0.012))
k += (k + 1) % 2
ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, ker, iterations=2)

ff = m.copy()
mask2 = np.zeros((h + 2, w + 2), np.uint8)
cv2.floodFill(ff, mask2, (0, 0), 1)
holes = (ff == 0).astype(np.uint8)
m = np.clip(m + holes, 0, 1).astype(np.uint8)
print("after close+fill:", int(m.sum()), f"({m.mean()*100:.1f}%)")

cv2.imwrite(DIAG + "01_mask.png", (m * 255))

# ---- 4. soft alpha --------------------------------------------------------
soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(1.0, min(w, h) * 0.004))
soft = np.clip((soft - 0.35) / 0.30, 0, 1)
cv2.imwrite(DIAG + "02_mask_soft.png", (soft * 255).astype(np.uint8))

# ---- 5. composites --------------------------------------------------------
rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

check = np.zeros_like(rgb)
yy, xx = np.mgrid[0:h, 0:w]
cell = max(16, min(w, h) // 24)
pat = ((yy // cell) + (xx // cell)) % 2
check[pat == 0] = (230, 60, 200)
check[pat == 1] = (60, 220, 140)
comp = rgb * soft[..., None] + check * (1 - soft[..., None])
Image.fromarray(np.clip(comp, 0, 255).astype(np.uint8)).save(DIAG + "03_checker.png")

flat = np.full_like(rgb, 150.0)
comp2 = rgb * soft[..., None] + flat * (1 - soft[..., None])
Image.fromarray(np.clip(comp2, 0, 255).astype(np.uint8)).save(DIAG + "04_graybg.png")

ann = rgb.copy()
cont, _ = cv2.findContours((m * 255), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(ann, cont, -1, (255, 0, 0), 2)
Image.fromarray(np.clip(ann, 0, 255).astype(np.uint8)).save(DIAG + "05_orig_annot.png")

np.save(BASE + "alpha_v1.npy", soft.astype(np.float32))
print("diagnostics written to", DIAG)
