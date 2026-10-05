"""Final deliverable: replace ONLY the background, using the best mask found.

Decision record
---------------
Automated figure/background separation on this image has no stable solution:
  - GrabCut alone          -> 46% ; hair tips at the crown read as background,
                              so ORIGINAL bg survives inside the new area
  - GrabCut + detail union -> 72% ; swallows the background's architectural
                              shapes, so ORIGINAL bg is left in the frame
Narrowing the detail threshold only trades one failure for the other.

The mask used here is GrabCut + exterior-hole fill (the 46.9% variant), which
gives a clean, tight silhouette. Its known limitation is the pale glow where
the semi-transparent hair tips meet the background; that region is left on the
ORIGINAL pixels, so no character data is invented or destroyed.

Guarantee verified at runtime: every pixel inside the mask is bit-identical to
the original.
"""
import os
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
import cv2
import numpy as np

BASE = f"{_MANTU_ROOT_STR}/compose/"
OUT = BASE + "deliver/"
os.makedirs(OUT, exist_ok=True)

orig = cv2.imread(BASE + "base_v1.png", cv2.IMREAD_COLOR)
h, w = orig.shape[:2]

# ---- mask ----------------------------------------------------------------
gm = np.zeros((h, w), np.uint8)
rect = (int(w * 0.06), int(h * 0.02), int(w * 0.92), int(h * 0.96))
cv2.grabCut(orig, gm, rect, np.zeros((1, 65), np.float64),
            np.zeros((1, 65), np.float64), 6, cv2.GC_INIT_WITH_RECT)
m = np.where((gm == cv2.GC_FGD) | (gm == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
num, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
if num > 1:
    m = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)

k = max(3, int(min(w, h) * 0.014)); k += (k + 1) % 2
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)), iterations=2)
# fill exterior-interior holes (the neck/chest island)
cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
solid = np.zeros((h, w), np.uint8)
cv2.drawContours(solid, cnts, -1, 1, thickness=cv2.FILLED)

# ---- new background: smooth, texture-free, 灰绿, one left->right gradient --
smooth = cv2.GaussianBlur(orig, (0, 0), min(w, h) * 0.055)
bg = cv2.inpaint(smooth, (solid * 255).astype(np.uint8), 5, cv2.INPAINT_TELEA)
bg = cv2.GaussianBlur(bg, (0, 0), min(w, h) * 0.030)

bf = bg.astype(np.float32)
lum = bf @ np.array([0.114, 0.587, 0.299], np.float32)
tgt = np.stack([lum * 0.985, lum * 1.005, lum * 1.015], axis=-1)
bg = np.clip(0.55 * bf + 0.45 * tgt, 0, 255).astype(np.uint8)

# ---- outward-only feathered blend ---------------------------------------
tight = cv2.erode(solid, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
grow = int(min(w, h) * 0.007)   # was 0.040: a wide band left the ORIGINAL
                                # (brighter) background visible as a halo
outer = cv2.dilate(tight, cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1)))
dist = cv2.distanceTransform((1 - tight).astype(np.uint8), cv2.DIST_L2, 5)
feather = np.where(outer > 0, np.clip(1.0 - dist / float(grow), 0, 1), 0.0).astype(np.float32)
feather[tight > 0] = 1.0
feather = cv2.GaussianBlur(feather, (0, 0), grow * 0.22)
feather = np.clip((feather - 0.03) / 0.94, 0, 1)
feather[solid > 0] = 1.0

mix = (orig.astype(np.float32) * feather[..., None]
       + bg.astype(np.float32) * (1 - feather[..., None]))
mix = np.clip(mix, 0, 255).astype(np.uint8)

ok = np.array_equal(mix[solid > 0], orig[solid > 0])
print("figure pixels bit-identical:", ok)
assert ok, "figure pixels were modified!"

# ---- deliverables -------------------------------------------------------
cv2.imwrite(OUT + "01_result.png", mix)                       # the composite
cv2.imwrite(OUT + "02_background_only.png", bg)               # bg plate alone
cv2.imwrite(OUT + "03_original.png", orig)                    # reference
# mask guide: white = figure (fully protected), gray = transition band
guide = np.full((h, w), 255, np.uint8)
guide[(outer > 0) & (solid == 0)] = 128
guide[solid > 0] = 0
cv2.imwrite(OUT + "04_mask_guide.png", guide)
# side by side
sbs = np.concatenate([orig, np.full((h, 12, 3), 255, np.uint8), mix], axis=1)
cv2.imwrite(OUT + "05_side_by_side.png", sbs)

c = cv2.cvtColor(mix, cv2.COLOR_BGR2RGB).astype(np.float32)
print("col means:", [round(float(c[:, j*w//12:(j+1)*w//12].mean()), 1) for j in range(12)])
print("original  :", [round(float(a[:, j*w//12:(j+1)*w//12].mean()), 1)
                      for j, a in [(j, cv2.cvtColor(orig, cv2.COLOR_BGR2RGB).astype(np.float32)) for j in range(12)]])
print("files in", OUT)
for f in sorted(os.listdir(OUT)):
    print("   ", f)
