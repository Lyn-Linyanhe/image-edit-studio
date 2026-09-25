"""Prove whether the relay honours the `mask` parameter at all.

A: edit WITH mask (mask = top half editable)
B: edit WITHOUT any mask
C: edit with the mask under an alternate field name

If A and B are (near) identical in the protected region, the relay drops `mask`.
"""
import base64
import hashlib
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
MODEL = "gpt-image-2"
SIZE = "1024x1024"
H = W = 1024


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


def post(fields, files, timeout=600):
    bnd = ("----Live" + uuid.uuid4().hex).encode()
    body = build_multipart(fields, files, bnd)
    req = urllib.request.Request(BASE + "/images/edits", data=body, method="POST")
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


def image_bytes(text):
    d = json.loads(text)
    it = (d.get("data") or [{}])[0]
    if it.get("b64_json"):
        return base64.b64decode(it["b64_json"])
    if it.get("url"):
        with urllib.request.urlopen(it["url"], timeout=180,
                                    context=ssl.create_default_context()) as r:
            return r.read()
    return None


# base: white top, blue bottom
a = np.zeros((H, W, 3), np.uint8)
a[: H // 2] = [245, 245, 245]
a[H // 2:] = [30, 60, 200]
ibuf = io.BytesIO()
Image.fromarray(a, "RGB").save(ibuf, "PNG", optimize=True)
img_png = ibuf.getvalue()

# mask: top half editable (alpha 0), bottom protected (alpha 255)
m = np.zeros((H, W, 4), np.uint8)
m[: H // 2, :, 3] = 0
m[H // 2:, :, 3] = 255
mbuf = io.BytesIO()
Image.fromarray(m, "RGBA").save(mbuf, "PNG", optimize=True)
mask_png = mbuf.getvalue()

PROMPT = "Replace the painted area with a flat orange color."

runs = {
    "A_with_mask":   {"mask": ("mask.png", mask_png, "image/png")},
    "B_no_mask":     {},
}

results = {}
for tag, extra in runs.items():
    print(f"--- {tag} ---")
    files = {"image": ("image.png", img_png, "image/png")}
    files.update(extra)
    st, txt = post({"model": MODEL, "prompt": PROMPT, "size": SIZE,
                    "n": "1", "quality": "low"}, files)
    if st != 200:
        print(f"   HTTP {st}  {txt[:300]}")
        results[tag] = None
        continue
    raw = image_bytes(txt)
    if not raw:
        print("   no image")
        results[tag] = None
        continue
    open(f"_cmp_{tag}.png", "wb").write(raw)
    arr = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB")).astype(int)
    top = arr[: H // 2].reshape(-1, 3).mean(axis=0)
    bot = arr[H // 2:].reshape(-1, 3).mean(axis=0)
    preserved = bot[2] > 150 and (bot[2] - bot[0]) > 60
    results[tag] = {"top": top, "bot": bot, "kept": preserved,
                    "sha": hashlib.sha256(raw).hexdigest()[:12]}
    print(f"   top  mean {top.round(0)}   bottom mean {bot.round(0)}")
    print(f"   protected region preserved: {preserved}   sha={results[tag]['sha']}")

print("\n================ VERDICT ================")
A, B = results.get("A_with_mask"), results.get("B_no_mask")
if A and B:
    dtop = np.abs(A["top"] - B["top"]).mean()
    dbot = np.abs(A["bot"] - B["bot"]).mean()
    print(f"with-mask vs without-mask:  top diff {dtop:.1f},  bottom diff {dbot:.1f}")
    print(f"identical output bytes: {A['sha'] == B['sha']}")
    if A["kept"] is False and B["kept"] is False:
        print(">>> MASK IS IGNORED: the protected half was rewritten even WITH a mask,")
        print("    and the output matches the no-mask run. This relay does not")
        print("    perform masked inpainting on /images/edits.")
    elif A["kept"] and not B["kept"]:
        print(">>> MASK WORKS with the standard convention.")
    elif not A["kept"] and B["kept"]:
        print(">>> MASK WORKS but the semantics are INVERTED (use mask_mode=inv).")
else:
    print("could not compare (a run failed)")
