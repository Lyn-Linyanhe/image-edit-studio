"""Download the Grok outputs and measure them, so we know what the engine
actually produces (size, palette behaviour, whether edits preserve the input)."""
import base64
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 2)))
import io
import json
import ssl
import urllib.request

import numpy as np
from PIL import Image

BASE = "https://image-direct.geiliapi.com/v1"
KEY = ""


def sj(path, obj, timeout=600):
    r = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(), method="POST")
    r.add_header("Content-Type", "application/json")
    r.add_header("Authorization", "Bearer " + KEY)
    with urllib.request.urlopen(r, timeout=timeout, context=ssl.create_default_context()) as x:
        return json.loads(x.read().decode("utf-8", "replace"))


def fetch(item):
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    u = item.get("url")
    if not u:
        return None
    with urllib.request.urlopen(u, timeout=180, context=ssl.create_default_context()) as x:
        return x.read()


def stats(a):
    sat = a.max(axis=2) - a.min(axis=2)
    g = a.mean(axis=2)
    return (a.reshape(-1, 3).mean(axis=0).round(0), g.mean(), g.std(), sat.mean())


print("=== text-to-image, resolution sweep ===")
for res, size in (("1k", "1024x1024"), ("2k", "2048x2048")):
    try:
        d = sj("/images/generations", {
            "model": "grok-imagine",
            "prompt": "a quiet misty gray-green landscape, soft low contrast light",
            "n": 1, "resolution": res, "size": size})
        raw = fetch((d.get("data") or [{}])[0])
        if raw:
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            a = np.asarray(im).astype(np.float32)
            print(f"  {res:3s} -> {im.size}  {len(raw)//1024} KB  mean {stats(a)[0]} "
                  f"sat {stats(a)[3]:.1f}")
            if res == "1k":
                im.save("_grok_t2i.png")
                d = sj("/images/generations", {
                    "model": "grok-imagine",
                    "prompt": "a quiet misty gray-green landscape, soft low contrast light",
                    "n": 1, "resolution": "1k", "size": "1024x1024"})
    except Exception as e:
        print(f"  {res:3s} -> FAILED {type(e).__name__}: {e}")

print("\n=== image-to-image: does it preserve the input? ===")
ref_im = Image.open(f"{_MANTU_ROOT_STR}/compose/input_red.jpg").convert("RGB")
ref_small = ref_im.resize((768, 768))
b = io.BytesIO(); ref_small.save(b, "PNG", optimize=True)
ref_png = b.getvalue()

import uuid
bnd = ("----G" + uuid.uuid4().hex).encode()
out = bytearray()
for k, v in {"model": "grok-imagine-edit",
             "prompt": "reduce saturation to a muted gray-green palette, keep the composition",
             "resolution": "1k", "size": "1024x1024"}.items():
    out += b"--" + bnd + b"\r\n"
    out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
    out += str(v).encode("utf-8") + b"\r\n"
out += b"--" + bnd + b"\r\n"
out += b'Content-Disposition: form-data; name="image"; filename="image.png"\r\n'
out += b"Content-Type: image/png\r\n\r\n" + ref_png + b"\r\n"
out += b"--" + bnd + b"--\r\n"

r = urllib.request.Request(BASE + "/images/edits", data=bytes(out), method="POST")
r.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
r.add_header("Authorization", "Bearer " + KEY)
with urllib.request.urlopen(r, timeout=600, context=ssl.create_default_context()) as x:
    d = json.loads(x.read().decode("utf-8", "replace"))
raw = fetch((d.get("data") or [{}])[0])
if raw:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.save("_grok_i2i.png")
    a = np.asarray(im).astype(np.float32)
    src = np.asarray(ref_small).astype(np.float32)
    print(f"  input  {ref_small.size}  mean {stats(src)[0]}  sat {stats(src)[3]:.1f}")
    print(f"  output {im.size}  {len(raw)//1024} KB  mean {stats(a)[0]}  sat {stats(a)[3]:.1f}")
    rr = np.asarray(im.resize(ref_small.size)).astype(np.float32)
    diff = np.abs(rr - src).mean(axis=2)
    print(f"  mean abs diff vs input: {diff.mean():.1f}   (low = composition preserved)")
    print(f"  saved _grok_i2i.png")
else:
    print("  no image returned:", str(d)[:300])
