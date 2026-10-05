"""Isolate the mask transform: canvas mask -> forwarded mask."""
import io
import numpy as np
from PIL import Image
import mask_edit_app as app

W, H = 900, 1330
# canvas mask: transparent everywhere, opaque WHITE on left+right bands
mpx = np.zeros((H, W, 4), np.uint8)
mpx[:, :140] = [255, 255, 255, 255]
mpx[:, -140:] = [255, 255, 255, 255]
canvas_mask = Image.fromarray(mpx, "RGBA")
print("canvas mask: painted(band) alpha =", mpx[0, 0, 3], " unpainted(centre) alpha =", mpx[H//2, W//2, 3])

tw, th, pad = 1024, 1536, "pad"
src = Image.new("RGB", (W, H), (200, 120, 120))
img_fit = app.normalise_to_size(src, tw, th, pad)

s = min(tw / W, th / H)
nw, nh = max(1, round(W * s)), max(1, round(H * s))
ox, oy = (tw - nw) // 2, (th - nh) // 2
print(f"letterbox: nw={nw} nh={nh} ox={ox} oy={oy}")

cm = canvas_mask.resize((nw, nh), Image.LANCZOS)
padded = Image.new("L", (tw, th), 0)
padded.paste(cm.split()[3].point(lambda v: 255 if v > 127 else 0), (ox, oy))
arr = np.asarray(padded)
print("padded mask: corner =", arr[5, 5], " centre =", arr[th//2, tw//2],
      " painted px % =", round(float((arr > 127).mean()) * 100, 1))

for mode in ("std", "inv"):
    painted = arr > 127
    if mode == "inv":
        painted = ~painted
    out = np.zeros((th, tw, 4), np.uint8)
    out[:, :, 3] = np.where(painted, 0, 255).astype(np.uint8)
    print(f"  mode={mode:4s} corner_alpha={out[5,5,3]:3d} centre_alpha={out[th//2,tw//2,3]:3d} "
          f"transparent%={round(float((out[:,:,3]==0).mean())*100,1)}")

# sanity: is the band actually landing on the left/right edges after padding?
band_cols = np.where((arr > 127).any(axis=0))[0]
print("painted columns span:", band_cols.min(), "..", band_cols.max(), f"(width {tw})")
