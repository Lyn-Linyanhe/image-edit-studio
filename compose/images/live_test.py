"""Live test against the real relay: does /images/edits + mask work?"""
import base64
import io
import json
import ssl
import sys
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

BASE = "https://image-direct.geiliapi.com/v1"
KEY = "sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915"
MODEL = "gpt-image-2"
SIZE = "1024x1024"


def build_multipart(fields, files, boundary):
    out = bytearray()
    for k, v in fields.items():
        out += b"--" + boundary + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        out += str(v).encode() + b"\r\n"
    for k, (fn, data, ct) in files.items():
        out += b"--" + boundary + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'.encode()
        out += f"Content-Type: {ct}\r\n\r\n".encode()
        out += data + b"\r\n"
    out += b"--" + boundary + b"--\r\n"
    return bytes(out)


def post(path, fields, files, timeout=600):
    bnd = ("----Live" + uuid.uuid4().hex).encode()
    body = build_multipart(fields, files, bnd)
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    req.add_header("Authorization", "Bearer " + KEY)
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def save_result(text, tag):
    d = json.loads(text)
    it = (d.get("data") or [{}])[0]
    raw = None
    if it.get("b64_json"):
        raw = base64.b64decode(it["b64_json"])
    elif it.get("url"):
        with urllib.request.urlopen(it["url"], timeout=180,
                                    context=ssl.create_default_context()) as r:
            raw = r.read()
    if raw:
        open(tag + ".png", "wb").write(raw)
        im = Image.open(io.BytesIO(raw))
        print(f"   saved {tag}.png  {im.size}  {len(raw)//1024} KB")
        return im
    print("   no image in response")
    return None


# ---- base image: white top half, BLUE bottom half -------------------------
W = H = 1024
a = np.zeros((H, W, 3), np.uint8)
a[: H // 2] = [245, 245, 245]          # white top  -> paint this = change it
a[H // 2:] = [30, 60, 200]             # blue bottom -> must stay untouched
base_img = Image.fromarray(a, "RGB")
base_img.save("_live_input.png")

# ---- mask: PAINT the top half (white = change), bottom stays clear --------
mpx = np.zeros((H, W, 4), np.uint8)
mpx[: H // 2] = [255, 255, 255, 255]
canvas_mask = Image.fromarray(mpx, "RGBA")
canvas_mask.save("_live_mask.png")

# convert to the OpenAI convention the app uses: painted -> alpha 0
out = np.zeros((H, W, 4), np.uint8)
out[:, :, 3] = np.where(mpx[:, :, 3] > 127, 0, 255).astype(np.uint8)
mbuf = io.BytesIO()
Image.fromarray(out, "RGBA").save(mbuf, "PNG", optimize=True)
mask_png = mbuf.getvalue()
ibuf = io.BytesIO()
base_img.save(ibuf, "PNG", optimize=True)

print("input : white top half (editable), blue bottom half (must survive)")
print("mask  : top half alpha=0 (editable), bottom alpha=255 (protected)")
print()

for label, mode in (("STD (painted=editable)", "std"), ("INV (painted=protected)", "inv")):
    m = mask_png
    if mode == "inv":
        o2 = np.zeros((H, W, 4), np.uint8)
        o2[:, :, 3] = np.where(mpx[:, :, 3] > 127, 255, 0).astype(np.uint8)
        b2 = io.BytesIO()
        Image.fromarray(o2, "RGBA").save(b2, "PNG", optimize=True)
        m = b2.getvalue()
    print(f"--- {label} ---")
    st, txt = post("/images/edits", {
        "model": MODEL,
        "prompt": "Replace this area with a soft flat orange gradient. Plain orange only.",
        "size": SIZE, "n": "1", "quality": "low",
    }, {"image": ("image.png", ibuf.getvalue(), "image/png"),
        "mask": ("mask.png", m, "image/png")})
    print(f"   HTTP {st}")
    if st == 200:
        try:
            im = save_result(txt, "_live_out_" + mode)
            if im:
                arr = np.asarray(im.convert("RGB")).astype(int)
                top = arr[: H // 2].reshape(-1, 3).mean(axis=0)
                bot = arr[H // 2:].reshape(-1, 3).mean(axis=0)
                print(f"   top half mean RGB {top.round(0)}  (was white 245,245,245)")
                print(f"   bottom half mean RGB {bot.round(0)}  (was blue 30,60,200)")
                blue_kept = bot[2] > 150 and bot[2] - bot[0] > 60
                print(f"   >>> bottom (protected) preserved: {blue_kept}")
        except Exception as e:
            print("   parse error:", e, txt[:300])
    else:
        print("   ", txt[:600])
    print()
