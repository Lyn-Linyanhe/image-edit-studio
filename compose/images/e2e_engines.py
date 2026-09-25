"""End-to-end test of the multi-engine app through its own HTTP endpoint.

Covers:
  A. GPT engine, image-to-image, whole-image   -> should succeed
  B. Grok engine, TEXT-to-image                -> should succeed (b64 inline)
  C. Grok engine, image-to-image               -> expected to FAIL with the
     explicit "imgen.x.ai unreachable" message; we assert the message is
     actionable rather than a generic error
  D. Grok engine, mask mode                    -> should be refused up front
"""
import base64
import io
import json
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

APP = "http://127.0.0.1:8000"
GROK_KEY = ""
GPT_KEY = ""
BASE = "https://image-direct.geiliapi.com/v1"
FAILS = []


def check(cond, label, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  {detail}" if detail else ""))
    if not cond:
        FAILS.append(label)


def post(fields, files=None, timeout=900):
    bnd = ("----E2E" + uuid.uuid4().hex).encode()
    out = bytearray()
    for k, v in fields.items():
        out += b"--" + bnd + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        out += str(v).encode("utf-8") + b"\r\n"
    for k, (fn, data, ct) in (files or {}).items():
        out += b"--" + bnd + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'.encode()
        out += f"Content-Type: {ct}\r\n\r\n".encode()
        out += data + b"\r\n"
    out += b"--" + bnd + b"--\r\n"
    r = urllib.request.Request(APP + "/api/edit", data=bytes(out), method="POST")
    r.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as x:
            return json.loads(x.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}


def png(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


src = Image.open("C:/Users/typ/Desktop/mantu/compose/input_red.jpg").convert("RGB")
src_fit = src.resize((1024, 1024))
img_png = png(src_fit)
# a canvas mask that paints everything except a central slab
mx = np.zeros((1024, 1024, 4), np.uint8)
mx[:, :, 3] = 255
mx[200:900, 250:780, 3] = 0
mask_png = png(Image.fromarray(mx, "RGBA"))


def save(j, name):
    if not j.get("ok"):
        return None
    raw = base64.b64decode(j["image_b64"])
    open(name, "wb").write(raw)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    sat = (a.max(axis=2) - a.min(axis=2)).mean()
    print(f"      -> {name}  {im.size}  {len(raw)//1024} KB  mean "
          f"{a.reshape(-1,3).mean(axis=0).round(0)}  sat {sat:.1f}")
    return im


print("=== A. GPT engine · image-to-image · whole image ===")
j = post({"engine": "gpt", "operation": "i2i", "base_url": BASE, "api_key": GPT_KEY,
          "model": "gpt-image-2", "prompt": "改为低饱和灰绿调，保留人物与构图",
          "size": "1024x1024", "quality": "low", "pad_mode": "crop",
          "mask_mode": "std", "scope": "whole"},
         {"image_file": ("image.png", img_png, "image/png")})
check(j.get("ok") is True, "GPT i2i whole succeeds", str(j.get("message"))[:150])
save(j, "e2e_A_gpt_i2i.png")

print("\n=== B. Grok engine · TEXT-to-image ===")
j = bot = post({"engine": "grok", "operation": "t2i", "base_url": BASE, "api_key": GROK_KEY,
                "model": "grok-imagine", "prompt": "a quiet misty gray-green landscape",
                "size": "1024x1024", "quality": "low", "resolution": "1k",
                "pad_mode": "crop", "mask_mode": "std", "scope": "whole"})
check(j.get("ok") is True, "Grok t2i succeeds", str(j.get("message"))[:150])
im = save(j, "e2e_B_grok_t2i.png")
if im is not None:
    check(im.size == (1024, 1024), "Grok t2i output is 1024x1024", str(im.size))

print("\n=== C. Grok engine · image-to-image (expected failure, must be explained) ===")
j = post({"engine": "grok", "operation": "i2i", "base_url": BASE, "api_key": GROK_KEY,
          "model": "grok-imagine-edit", "prompt": "muted gray-green palette",
          "size": "1024x1024", "quality": "low", "resolution": "1k",
          "pad_mode": "crop", "mask_mode": "std", "scope": "whole"},
         {"image_file": ("image.png", img_png, "image/png")})
msg = str(j.get("message", ""))
if j.get("ok"):
    print("      (succeeded - the CDN may be reachable after all)")
    save(j, "e2e_C_grok_i2i.png")
else:
    check("imgen.x.ai" in msg, "failure names the unreachable host")
    check("不支持内联 base64" in msg or "无法访问" in msg,
          "failure explains why, in Chinese", msg.replace("\n", " | ")[:150])
    print("      message:")
    for line in msg.splitlines()[:5]:
        print("        " + line)

print("\n=== D. Grok engine · mask mode must be refused up front ===")
j = post({"engine": "grok", "operation": "i2i", "base_url": BASE, "api_key": GROK_KEY,
          "model": "grok-imagine-edit", "prompt": "x", "size": "1024x1024",
          "quality": "low", "resolution": "1k", "pad_mode": "crop",
          "mask_mode": "std", "scope": "mask"},
         {"image_file": ("image.png", img_png, "image/png"),
          "mask_file": ("mask.png", mask_png, "image/png")})
check(j.get("ok") is False, "Grok mask mode rejected")
check("遮罩" in str(j.get("message", "")), "rejection mentions the mask limitation",
      str(j.get("message", "")).replace("\n", " ")[:120])

print("\n" + "=" * 58)
print("FAILED:", len(FAILS), FAILS if FAILS else "(all passed)")
print("=" * 58)
