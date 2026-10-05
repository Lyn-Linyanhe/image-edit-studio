"""Probe the Grok Imagine key: text-to-image and image-to-image.

Follows the supplied spec exactly:
  generations : JSON {model, prompt, n, resolution, size}
  edits       : multipart {model, prompt, resolution, size, image[, image[1..]]}
Note the spec's own warning: do NOT send OpenAI `quality` to these models.
"""
import base64
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 2)))
import io
import json
import ssl
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

BASE = "https://image-direct.geiliapi.com/v1"
KEY = ""


def sj(path, obj, timeout=600):
    body = json.dumps(obj).encode()
    r = urllib.request.Request(BASE + path, data=body, method="POST")
    r.add_header("Content-Type", "application/json")
    r.add_header("Authorization", "Bearer " + KEY)
    try:
        with urllib.request.urlopen(r, timeout=timeout,
                                    context=ssl.create_default_context()) as x:
            return x.status, x.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def sm(path, fields, files, timeout=600):
    bnd = ("----Grok" + uuid.uuid4().hex).encode()
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
    r = urllib.request.Request(BASE + path, data=bytes(out), method="POST")
    r.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    r.add_header("Authorization", "Bearer " + KEY)
    try:
        with urllib.request.urlopen(r, timeout=timeout,
                                    context=ssl.create_default_context()) as x:
            return x.status, x.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def report(tag, st, txt):
    if st == 200:
        try:
            d = json.loads(txt)
            it = (d.get("data") or [{}])[0]
            kind = "b64_json" if it.get("b64_json") else ("url" if it.get("url") else "NONE")
            extra = ""
            if it.get("b64_json"):
                raw = base64.b64decode(it["b64_json"])
                im = Image.open(io.BytesIO(raw))
                extra = f"  image {im.size}  {len(raw)//1024} KB"
                out = f"_grok_{tag}.png"
                open(out, "wb").write(raw)
                extra += f"  -> {out}"
            elif it.get("url"):
                extra = f"  url {it['url'][:80]}"
            print(f"  {tag:34s} HTTP 200  {kind}{extra}")
            return True
        except Exception as e:
            print(f"  {tag:34s} HTTP 200  parse error: {e}  {txt[:200]}")
            return False
    print(f"  {tag:34s} HTTP {st}")
    try:
        err = json.loads(txt).get("error", {})
        msg = err.get("message") or txt
    except Exception:
        msg = txt
    print(f"      {str(msg)[:170]}")
    return False


print("=== 1. text-to-image: grok-imagine ===")
ok1 = report("grok-imagine res=1k",
             *sj("/images/generations", {
                 "model": "grok-imagine",
                 "prompt": "a quiet gray-green misty landscape, soft light",
                 "n": 1, "resolution": "1k", "size": "1024x1024"}))

print("\n=== 2. text-to-image: grok-imagine-image (faster) ===")
ok2 = report("grok-imagine-image res=1k",
             *sj("/images/generations", {
                 "model": "grok-imagine-image",
                 "prompt": "a quiet gray-green misty landscape, soft light",
                 "n": 1, "resolution": "1k", "size": "1024x1024"}))

# build a small reference image
ref = Image.fromarray(np.asarray(
    Image.open(f"{_MANTU_ROOT_STR}/compose/input_red.jpg").convert("RGB")
    .resize((512, 512))), "RGB")
b = io.BytesIO(); ref.save(b, "PNG", optimize=True)
ref_png = b.getvalue()

print("\n=== 3. image-to-image: grok-imagine-edit (1 ref) ===")
ok3 = report("grok-imagine-edit 1 ref",
             *sm("/images/edits",
                 {"model": "grok-imagine-edit",
                  "prompt": "lower the saturation to a muted gray-green palette",
                  "resolution": "1k", "size": "1024x1024"},
                 {"image": ("image.png", ref_png, "image/png")}))

print("\n=== 4. image-to-image with an extra reference (image[1]) ===")
b2 = io.BytesIO()
Image.open(f"{_MANTU_ROOT_STR}/compose/style_ref.png").convert("RGB") \
    .resize((512, 512)).save(b2, "PNG", optimize=True)
style_png = b2.getvalue()
ok4 = report("grok-imagine-edit 2 refs",
             *sm("/images/edits",
                 {"model": "grok-imagine-edit",
                  "prompt": "use the technique of the second image, keep colours of the first",
                  "resolution": "1k", "size": "1024x1024"},
                 {"image": ("image.png", ref_png, "image/png"),
                  "image[1]": ("style.png", style_png, "image/png")}))

print("\n=== 5. does it reject OpenAI `quality`? (control) ===")
ok5 = report("generations with quality=low",
             *sj("/images/generations", {
                 "model": "grok-imagine", "prompt": "test",
                 "n": 1, "quality": "low", "resolution": "1k",
                 "size": "1024x1024"}))

print("\n=== 6. models list on this key ===")
r = urllib.request.Request(BASE + "/models")
r.add_header("Authorization", "Bearer " + KEY)
try:
    with urllib.request.urlopen(r, timeout=40,
                                context=ssl.create_default_context()) as x:
        ids = sorted(m.get("id", "") for m in json.loads(x.read().decode()).get("data", []))
        print("  ", ids)
except Exception as e:
    print("   failed:", e)

print("\n=== summary ===")
for i, ok in enumerate([ok1, ok2, ok3, ok4, ok5], 1):
    print(f"  case {i}: {'OK' if ok else 'FAILED'}")
