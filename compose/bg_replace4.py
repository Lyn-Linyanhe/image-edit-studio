"""Background-only replacement, v4 - hybrid matte.

Root cause of the halos: GrabCut reads the pale, soft hair tips at the top of
the head as background, so the mask undershoots there and the ORIGINAL
background survives inside the "already new" region, producing pale blade
notches.

Strategy here:
  A. GrabCut  -> coarse figure region
  B. local-detail salience -> the figure is full of brush detail, the
     background is a smooth gradient. Blur-and-difference detects the figure
     independently of colour.
  C. union A|B, then CLOSE hard (fills the soft hair tips), keep the largest
     component, fill holes, and CHAIN_APPROX_SIMPLE-smooth the contour so the
     boundary is clean rather than jagged.
  D. build the new background from blur+inpaint, and blend outward only.
"""
import os
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
import cv2
import numpy as np

BASE = f"{_MANTU_ROOT_STR}/compose/"
OUT = BASE + "final2/"
os.makedirs(OUT, exist_ok=True)

bgr = cv2.imread(BASE + "base_v1.png", cv2.IMREAD_COLOR)
h, w = bgr.shape[:2]
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

# ---- A. grabcut -----------------------------------------------------------
gmask = np.zeros((h, w), np.uint8)
rect = (int(w * 0.05), int(h * 0.01), int(w * 0.94), int(h * 0.98))
cv2.grabCut(bgr, gmask, rect, np.zeros((1, 65), np.float64),
            np.zeros((1, 65), np.float64), 6, cv2.GC_INIT_WITH_RECT)
A = np.where((gmask == cv2.GC_FGD) | (gmask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)

# ---- B. local-detail salience --------------------------------------------
S = min(w, h) * 0.030
det = cv2.absdiff(gray, cv2.GaussianBlur(gray, (0, 0), S)).astype(np.float32)
det = cv2.GaussianBlur(det, (0, 0), S * 0.8)
det = cv2.normalize(det, None, 0, 1, cv2.NORM_MINMAX)
B = (det > 0.18).astype(np.uint8)
B = cv2.morphologyEx(B, cv2.MORPH_CLOSE,
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)), iterations=2)
B = cv2.morphologyEx(B, cv2.MORPH_OPEN,
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)), iterations=1)

# ---- C. combine -----------------------------------------------------------
C = np.clip(A + B, 0, 1).astype(np.uint8)
C = cv2.morphologyEx(C, cv2.MORPH_CLOSE,
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (49, 49)), iterations=2)
num, lab, stats, _ = cv2.connectedComponentsWithStats(C, 8)
if num > 1:
    C = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
cnts, _ = cv2.findContours(C, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
C = np.zeros((h, w), np.uint8)
cv2.drawContours(C, cnts, -1, 1, thickness=cv2.FILLED)
print(f"A(grabcut) {A.mean()*100:.1f}%  B(detail) {B.mean()*100:.1f}%  C(union) {C.mean()*100:.1f}%")

# ---- background ----------------------------------------------------------
smooth = cv2.GaussianBlur(bgr, (0, 0), min(w, h) * 0.055)
bg = cv2.inpaint(smooth, (C * 255).astype(np.uint8), 5, cv2.INPAINT_TELEA)
bg = cv2.GaussianBlur(bg, (0, 0), min(w, h) * 0.030)
bf = bg.astype(np.float32)
lum = bf @ np.array([0.114, 0.587, 0.299], np.float32)
tgt = np.stack([lum * 0.985, lum * 1.005, lum * 1.015], axis=-1)
bg = np.clip(0.55 * bf + 0.45 * tgt, 0, 255).astype(np.uint8)

# ---- asymmetric outward blend -------------------------------------------
tight = cv2.erode(C, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
grow = int(min(w, h) * 0.035)
outer = cv2.dilate(tight, cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1)))
dist = cv2.distanceTransform((1 - tight).astype(np.uint8), cv2.DIST_L2, 5)
feather = np.where(outer > 0, np.clip(1.0 - dist / float(grow), 0, 1), 0.0).astype(np.float32)
feather[tight > 0] = 1.0
feather = cv2.GaussianBlur(feather, (0, 0), grow * 0.20)
feather = np.clip((feather - 0.02) / 0.96, 0, 1)
feather[C > 0] = 1.0

mix = (bgr.astype(np.float32) * feather[..., None]
       + bg.astype(np.float32) * (1 - feather[..., None]))
mix = np.clip(mix, 0, 255).astype(np.uint8)

print("figure pixels bit-identical:", np.array_equal(mix[C > 0], bgr[C > 0]))
cv2.imwrite(OUT + "result.png", mix)
cv2.imwrite(OUT + "bg.png", bg)

ov = bgr.copy()
ov[outer == 0] = (255, 255, 255)
ov[(outer > 0) & (C == 0)] = (0, 255, 255)
cv2.imwrite(OUT + "mask_preview.png", ov)
print("saved", OUT)
