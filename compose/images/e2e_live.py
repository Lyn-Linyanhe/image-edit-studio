"""Full end-to-end run through the LOCAL APP against the real relay.

Uses the user's actual reference image (base_v1.png, 837x1243) and a mask that
paints the BACKGROUND (so only the background may change), then verifies
numerically that the protected character region survived.

The character is protected by a generous rectangle covering the head + long
hair slab; everything outside it is painted as editable.
"""
import base64
import io
import json
import ssl
import urllib.request
import uuid

import numpy as np
from PIL import Image

APP = "http://127.0.0.1:8000"
SRC = "C:/Users/typ/Desktop/mantu/compose/base_v1.png"
OUT = "C:/Users/typ/Desktop/mantu/compose/images/"

src = Image.open(SRC).convert("RGB")
W, H = src.size
print(f"source {W}x{H}")

# ---- canvas mask: PAINT the background, leave the character clear ---------
# clear (protected) rectangle around the character; painted elsewhere
mx = np.zeros((H, W, 4), np.uint8)
mx[150:1243, 230:640, 3] = 255          # protected band: face + hair + torso
canvas_mask = Image.fromarray(mx, "RGBA")
prot_frac = (mx[:, :, 3] > 127).mean() * 100
print(f"protected (unpainted) area: {prot_frac:.1f}%   painted/editable: {100-prot_frac:.1f}%")

# ---- protect-both-directions number to compare against --------------------
src_arr = np.asarray(src).astype(int)
prot_region = mx[:, :, 3] > 127

PROMPT = ("替换背景为无任何可辨认物体的平滑灰绿渐变：低饱和灰绿与灰橄榄色，"
          "左亮右暗的柔和明暗过渡，四角略暗，过渡处没有可见分界线。"
          "背景干净无纹理：不要纸张颗粒、不要水渍斑点、不要云絮雾状、不要涂抹笔触、"
          "不要建筑、墙面、地面、树木或任何地标。整体降低对比度，颜色偏灰。")

def multipart(fields, files):
    bnd = ("----E2E" + uuid.uuid4().hex).encode()
    out = bytearray()
    for k, v in fields.items():
        out += b"--" + bnd + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        out += str(v).encode() + b"\r\n"
    for k, (fn, data, ct) in files.items():
        out += b"--" + bnd + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'.encode()
        out += f"Content-Type: {ct}\r\n\r\n".encode()
        out += data + b"\r\n"
    out += b"--" + bnd + b"--\r\n"
    req = urllib.request.Request(APP + "/api/edit", data=bytes(out), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        return -1, {"ok": False, "message": f"{type(e).__name__}: {e}"}


def png_bytes(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


# 1K tier with a 2:3 portrait matches the source aspect closely
fields = {
    "base_url": "https://image-direct.geiliapi.com/v1",
    "api_key": "sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915",
    "model": "gpt-image-2",
    "prompt": PROMPT,
    "size": "1024x1536",
    "quality": "low",
    "pad_mode": "crop",          # 2:3 source -> 2:3 target, minimal loss
    "mask_mode": "std",
}
files = {
    "image_file": ("image.png", png_bytes(src), "image/png"),
    "mask_file": ("mask.png", png_bytes(canvas_mask), "image/png"),
}

print("\n--- sending through the local app ---")
st, j = multipart(fields, files)
print("app returned ok:", j.get("ok"), (j.get("message") or "")[:400])

if not j.get("ok"):
    raise SystemExit(1)

raw = base64.b64decode(j["image_b64"])
out_path = OUT + "e2e_result.png"
open(out_path, "wb").write(raw)
res = Image.open(io.BytesIO(raw)).convert("RGB")
print(f"saved {out_path}  {res.size}  {len(raw)//1024} KB")

# ---- verify the protected region survived --------------------------------
# map the protected region onto the 1024x1536 output with the same crop logic
tw, th = 1024, 1536
src_ar, tgt_ar = W / H, tw / th
if src_ar > tgt_ar:
    nw = int(H * tgt_ar); box = ((W - nw) // 2, 0, (W - nw) // 2 + nw, H)
else:
    nh = int(W / tgt_ar); box = (0, (H - nh) // 2, W, (H - nh) // 2 + nh)
crop = src.crop(box).resize((tw, th), Image.LANCZOS)
mres = Image.fromarray(mx, "RGBA").crop(box).resize((tw, th), Image.NEAREST)
keep = np.asarray(mres)[:, :, 3] > 127

a_src = np.asarray(crop).astype(float)
a_out = np.asarray(res).astype(float)
diff = np.abs(a_src - a_out).mean(axis=2)

print("\n--- numeric check ---")
print(f"protected pixels: {keep.sum():,} ({keep.mean()*100:.1f}% of frame)")
print(f"mean abs diff INSIDE protected region : {diff[keep].mean():6.1f}")
print(f"mean abs diff OUTSIDE (background)    : {diff[~keep].mean():6.1f}")
unchanged = (diff[keep] < 12).mean() * 100
print(f"protected pixels essentially unchanged : {unchanged:5.1f}%   (want high)")
print(f"background pixels changed              : {(diff[~keep] > 12).mean()*100:5.1f}%   (want high)")

# side by side
sbs = Image.new("RGB", (tw * 2 + 12, th), (255, 255, 255))
sbs.paste(crop, (0, 0))
sbs.paste(res, (tw + 12, 0))
sbs.save(OUT + "e2e_side_by_side.png")
print("\nsaved e2e_side_by_side.png (left = original, right = result)")
