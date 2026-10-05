"""Diagnose the e2e output numerically: is the model ignoring the instruction,
or is the check itself misaligned?
"""
import io
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 2)))
import numpy as np
from PIL import Image

SRC = f"{_MANTU_ROOT_STR}/compose/base_v1.png"
OUT = f"{_MANTU_ROOT_STR}/compose/images/"
res = Image.open(OUT + "e2e_result.png").convert("RGB")
src = Image.open(SRC).convert("RGB")
W, H = src.size
tw, th = res.size

# replicate the app's crop transform
src_ar, tgt_ar = W / H, tw / th
if src_ar > tgt_ar:
    nw = int(H * tgt_ar); box = ((W - nw) // 2, 0, (W - nw) // 2 + nw, H)
else:
    nh = int(W / tgt_ar); box = (0, (H - nh) // 2, W, (H - nh) // 2 + nh)
print("crop box:", box)

crop = np.asarray(src.crop(box).resize((tw, th), Image.LANCZOS)).astype(float)
out = np.asarray(res).astype(float)
diff = np.abs(crop - out).mean(axis=2)

# the protected rectangle used in the test, in ORIGINAL coords
prot = np.zeros((H, W), bool)
prot[150:1243, 230:640] = True
pm = np.asarray(Image.fromarray((prot * 255).astype(np.uint8)).crop(box).resize((tw, th), Image.NEAREST)) > 127

print(f"\noverall: mean diff {diff.mean():.1f}")
print(f"protected rect: mean diff {diff[pm].mean():.1f}   changed>12: {(diff[pm]>12).mean()*100:.1f}%")
print(f"outside rect  : mean diff {diff[~pm].mean():.1f}   changed>12: {(diff[~pm]>12).mean()*100:.1f}%")

# colour stats: did the background actually become gray-green?
def stats(a, m, label):
    px = a[m]
    if len(px) == 0:
        print(f"  {label}: empty"); return
    print(f"  {label:26s} R{px[:,0].mean():6.1f} G{px[:,1].mean():6.1f} B{px[:,2].mean():6.1f}"
          f"  sat(spread) {np.abs(px[:,0]-px[:,2]).mean():5.1f}")

print("\nbackground region colour:")
stats(crop, ~pm, "ORIGINAL outside rect")
stats(out, ~pm, "RESULT   outside rect")
print("figure region colour:")
stats(crop, pm, "ORIGINAL inside rect")
stats(out, pm, "RESULT   inside rect")

# is there any leftover RED from the marker image leaking into the output?
o = out.astype(int)
redish = (o[:, :, 0] > 150) & (o[:, :, 1] < 80) & (o[:, :, 2] < 80)
print(f"\nred-marker leakage into output: {redish.mean()*100:.2f}% of pixels")

# where exactly did the protected region change most?  -> 3x3 grid inside it
ys, xs = np.where(pm)
if len(ys):
    print("\ninside-rect diff by vertical third:")
    y0, y1 = ys.min(), ys.max()
    for k in range(3):
        a = y0 + (y1 - y0) * k // 3
        b = y0 + (y1 - y0) * (k + 1) // 3
        sel = pm.copy(); sel[:a] = False; sel[b:] = False
        if sel.any():
            print(f"   band {k}: mean diff {diff[sel].mean():6.1f}")

# luminance gradient of the new background, left->right
print("\nresult column means (background only, top 60 rows):")
top = pm[:60]
for j in range(8):
    x0, x1 = j * tw // 8, (j + 1) * tw // 8
    seg = out[:60, x0:x1]
    segm = pm[:60, x0:x1]
    if (~segm).any():
        px = seg[~segm]
        print(f"   col{j}: {px.mean(axis=0).round(1)}")
