"""Probe the relay's ACTUAL /images/edits schema (JSON + images[].image_url).

The error `images[].image_url is required` shows this endpoint takes JSON with
image URLs (data URLs are normally accepted), not multipart form data.
Try several plausible shapes and see which one is accepted, then check whether
a mask field is honoured.
"""
import base64
import io
import json
import ssl
import urllib.error
import urllib.request

import numpy as np
from PIL import Image

BASE = "https://image-direct.geiliapi.com/v1"
KEY = ""
MODEL = "gpt-image-2"
S = 1024


def data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode()


def post_json(path, obj, timeout=600):
    body = json.dumps(obj).encode()
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + KEY)
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


# base: white top / blue bottom. mask: top editable.
a = np.zeros((S, S, 3), np.uint8)
a[: S // 2] = [245, 245, 245]
a[S // 2:] = [30, 60, 200]
ib = io.BytesIO(); Image.fromarray(a, "RGB").save(ib, "PNG", optimize=True)
img_png = ib.getvalue()

m = np.zeros((S, S, 4), np.uint8)
m[: S // 2, :, 3] = 0
m[S // 2:, :, 3] = 255
mb = io.BytesIO(); Image.fromarray(m, "RGBA").save(mb, "PNG", optimize=True)
mask_png = mb.getvalue()

IMG = data_url(img_png)
MSK = data_url(mask_png)
PROMPT = "Replace the painted area with a flat orange color."

shapes = {
    "1_image_url_only": {
        "model": MODEL, "prompt": PROMPT, "size": "1024x1024",
        "images": [{"image_url": IMG}],
    },
    "2_plus_mask_url": {
        "model": MODEL, "prompt": PROMPT, "size": "1024x1024",
        "images": [{"image_url": IMG, "mask_url": MSK}],
    },
    "3_plus_mask": {
        "model": MODEL, "prompt": PROMPT, "size": "1024x1024",
        "images": [{"image_url": IMG, "mask": MSK}],
    },
    "4_mask_top_level": {
        "model": MODEL, "prompt": PROMPT, "size": "1024x1024",
        "images": [{"image_url": IMG}], "mask": MSK,
    },
}

for tag, body in shapes.items():
    st, txt = post_json("/images/edits", body)
    print(f"--- {tag} -> HTTP {st}")
    if st != 200:
        print("    ", txt[:260].replace("\n", " "))
        continue
    try:
        d = json.loads(txt)
        it = (d.get("data") or [{}])[0]
        raw = None
        if it.get("b64_json"):
            raw = base64.b64decode(it["b64_json"])
        elif it.get("url"):
            with urllib.request.urlopen(it["url"], timeout=180,
                                        context=ssl.create_default_context()) as r:
                raw = r.read()
        if not raw:
            print("     no image; keys:", list(d.keys()), txt[:200])
            continue
        open(f"_api_{tag}.png", "wb").write(raw)
        arr = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB")).astype(int)
        top = arr[: S // 2].reshape(-1, 3).mean(axis=0)
        bot = arr[S // 2:].reshape(-1, 3).mean(axis=0)
        kept = bot[2] > 150 and (bot[2] - bot[0]) > 60
        print(f"     saved _api_{tag}.png   top {top.round(0)}  bottom {bot.round(0)}"
              f"   protected kept: {kept}")
    except Exception as e:
        print("     parse error:", e, txt[:200])
