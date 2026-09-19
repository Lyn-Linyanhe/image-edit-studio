"""Does passing the mask as a 2nd reference image produce real masking?

Per the official spec the endpoint takes image, image[1], image[2], image[3] and
has NO mask field. So try feeding the mask as a second reference image, and also
probe whether an explicit `mask` field is silently accepted.

Also validates the spec's quality<->size pairing rule:
  low    -> 1024x1024 / 1536x1024 / 1024x1536
  medium -> 2048x2048 / 2048x1152 / 1152x2048
  high   -> 2880x2880 / 3840x2160 / 2160x3840
"""
import base64
import io
import json
import ssl
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

BASE = "https://image-direct.geiliapi.com/v1"
KEY = "sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915"
MODEL = "gpt-image-2"


def build_multipart(fields, files, boundary):
    out = bytearray()
    for k, v in fields.items():
        out += b"--" + boundary + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        out += str(v).encode() + b"\r\n"
    for k, payload in files.items():
        if len(payload) == 3:
            fn, data, ct = payload
        else:
            fn, data = payload
            ct = "image/png"
        out += b"--" + boundary + b"\r\n"
        out += f'Content-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'.encode()
        out += f"Content-Type: {ct}\r\n\r\n".encode()
        out += data + b"\r\n"
    out += b"--" + boundary + b"--\r\n"
    return bytes(out)


def edit(fields, files, timeout=700):
    bnd = ("----G" + uuid.uuid4().hex).encode()
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


def get_image(text, tag):
    d = json.loads(text)
    it = (d.get("data") or [{}])[0]
    raw = None
    if it.get("b64_json"):
        raw = base64.b64decode(it["b64_json"])
    elif it.get("url"):
        with urllib.request.urlopen(it["url"], timeout=200,
                                    context=ssl.create_default_context()) as r:
            raw = r.read()
    if not raw:
        return None
    open(f"_r2_{tag}.png", "wb").write(raw)
    return Image.open(io.BytesIO(raw)).convert("RGB")


S = 1024
a = np.zeros((S, S, 3), np.uint8)
a[: S // 2] = [245, 245, 245]          # edit region
a[S // 2:] = [30, 60, 200]             # must be preserved (blue)
ib = io.BytesIO(); Image.fromarray(a, "RGB").save(ib, "PNG", optimize=True)
image_png = ib.getvalue()

# mask: opaque over the region to EDIT (white) -> also render a red-on-white
# visual so a VLM/LLM watching the refs can read "this half is the target"
mv = np.zeros((S, S, 4), np.uint8)
mv[: S // 2] = [255, 255, 255, 255]
mb = io.BytesIO(); Image.fromarray(mv, "RGBA").save(mb, "PNG", optimize=True)
mask_alpha_png = mb.getvalue()

mvis = np.full((S, S, 3), 255, np.uint8)
mvis[: S // 2] = [255, 0, 0]
mb2 = io.BytesIO(); Image.fromarray(mvis, "RGB").save(mb2, "PNG", optimize=True)
mask_visual_png = mb2.getvalue()

PROMPT = ("The second reference image is a mask: the red area marks the only region to "
          "change, everything else must stay exactly as in the first image. "
          "Replace the red area with a flat orange color. Keep the blue lower half unchanged.")

tests = {
    "E_2nd_ref_visual": ({"model": MODEL, "prompt": PROMPT, "quality": "low",
                          "size": "1024x1024", "n": "1"},
                         {"image": ("image.png", image_png, "image/png"),
                          "image[1]": ("mask.png", mask_visual_png, "image/png")}),
    "F_mask_field":     ({"model": MODEL, "prompt": PROMPT, "quality": "low",
                          "size": "1024x1024", "n": "1"},
                         {"image": ("image.png", image_png, "image/png"),
                          "mask": ("mask.png", mask_alpha_png, "image/png")}),
    "G_control_nomask": ({"model": MODEL, "prompt": PROMPT.replace(
        "The second reference image is a mask: the red area marks the only region to "
        "change, everything else must stay exactly as in the first image. ", ""),
        "quality": "low", "size": "1024x1024", "n": "1"},
        {"image": ("image.png", image_png, "image/png")}),
}

for tag, (fields, files) in tests.items():
    print(f"--- {tag} ---")
    st, txt = edit(fields, files)
    if st != 200:
        print(f"    HTTP {st}  {txt[:250]}")
        print()
        continue
    try:
        im = get_image(txt, tag)
    except Exception as e:
        print("    parse error:", e, txt[:200]); print(); continue
    if im is None:
        print("    no image"); print(); continue
    arr = np.asarray(im).astype(int)
    top = arr[: S // 2].reshape(-1, 3).mean(axis=0)
    bot = arr[S // 2:].reshape(-1, 3).mean(axis=0)
    kept = bot[2] > 150 and (bot[2] - bot[0]) > 60
    print(f"    saved _r2_{tag}.png  {im.size}")
    print(f"    top(edit region) {top.round(0)}   bottom(should stay blue) {bot.round(0)}")
    print(f"    >>> protected half preserved: {kept}")
    print()
