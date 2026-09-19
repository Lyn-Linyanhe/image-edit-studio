"""Drive the app's real HTTP endpoint (no browser) and read back the exact error.

The direct relay call succeeds, so the failure must be between the browser and
the local server. This posts the same multipart shape the page builds and
prints whatever /api/edit answers.
"""
import io
import json
import uuid

import numpy as np
import urllib.request
from PIL import Image

APP = "http://127.0.0.1:8000"
BASE = "https://image-direct.geiliapi.com/v1"
KEY = "sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915"

SRC = "C:/Users/typ/Desktop/mantu/compose/base_v1.png"
src = Image.open(SRC).convert("RGB")
W, H = src.size
print(f"source {W}x{H}")

# canvas mask in DISPLAY coordinates: the page scales the image to <=900 wide
disp_w = min(W, 900)
scale = disp_w / W
dw, dh = round(W * scale), round(H * scale)
mx = np.zeros((dh, dw, 4), np.uint8)
mx[int(150 * scale):dh, int(230 * scale):int(640 * scale), 3] = 255
mask_img = Image.fromarray(mx, "RGBA")
print(f"canvas mask {dw}x{dh}  painted={(mx[:,:,3]>127).mean()*100:.1f}%")


def png(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


def post(fields, files):
    bnd = ("----Browser" + uuid.uuid4().hex).encode()
    out = bytearray()
    for k, v in fields.items():
        out += b"--" + bnd + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        out += str(v).encode("utf-8") + b"\r\n"
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
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return -1, {"ok": False, "message": f"{type(e).__name__}: {e}"}


PROMPT = ("替换背景为无任何可辨认物体的平滑灰绿渐变：低饱和灰绿与灰橄榄色，左亮右暗的柔和明暗过渡，"
          "四角略暗。背景干净无纹理：不要纸张颗粒、不要水渍斑点、不要云絮雾状、不要建筑或地标。")

cases = {
    "A. masked, crop, 1024x1536 low": dict(
        fields={"base_url": BASE, "api_key": KEY, "model": "gpt-image-2",
                "prompt": PROMPT, "size": "1024x1536", "quality": "low",
                "pad_mode": "crop", "mask_mode": "std", "scope": "mask"},
        files={"image_file": ("image.png", png(src), "image/png"),
               "mask_file": ("mask.png", png(mask_img), "image/png")}),
    "B. whole image, crop, 1024x1536 low": dict(
        fields={"base_url": BASE, "api_key": KEY, "model": "gpt-image-2",
                "prompt": PROMPT, "size": "1024x1536", "quality": "low",
                "pad_mode": "crop", "mask_mode": "std", "scope": "whole"},
        files={"image_file": ("image.png", png(src), "image/png")}),
    "C. masked, pad, 1024x1536 low": dict(
        fields={"base_url": BASE, "api_key": KEY, "model": "gpt-image-2",
                "prompt": PROMPT, "size": "1024x1536", "quality": "low",
                "pad_mode": "pad", "mask_mode": "std", "scope": "mask"},
        files={"image_file": ("image.png", png(src), "image/png"),
               "mask_file": ("mask.png", png(mask_img), "image/png")}),
}

for tag, c in cases.items():
    print(f"\n--- {tag} ---")
    st, j = post(c["fields"], c["files"])
    print("   http", st, " ok:", j.get("ok"))
    if j.get("ok"):
        n = len(j.get("image_b64") or "")
        print(f"   >>> SUCCESS, b64 length {n:,}")
        if n:
            raw = __import__("base64").b64decode(j["image_b64"])
            im = Image.open(io.BytesIO(raw))
            out = "C:/Users/typ/Desktop/mantu/compose/images/app_" + tag[0] + ".png"
            open(out, "wb").write(raw)
            print(f"   saved {out}  {im.size}")
    else:
        print("   MESSAGE:", str(j.get("message"))[:700])
