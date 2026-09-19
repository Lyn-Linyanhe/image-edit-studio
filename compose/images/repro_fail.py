"""Reproduce exactly what the app sends to the relay, and print the FULL response.

Mirrors mask_edit_app.api_edit: same field names, same multipart layout,
quality/size pairing, SCHEMA_PROMPT prefix, visual mask as image[1], and an
alpha mask in `mask`. Prints the raw body on any non-200 so the real cause is
visible instead of a generic "generation failed".
"""
import io
import json
import ssl
import sys
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

sys.path.insert(0, ".")
import mask_edit_app as app  # reuse the real builder + prompt

BASE = "https://image-direct.geiliapi.com/v1"
KEY = "sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915"
MODEL = "gpt-image-2"

SRC = "C:/Users/typ/Desktop/mantu/compose/base_v1.png"
src = Image.open(SRC).convert("RGB")
W, H = src.size
print(f"source {W}x{H}")


def run(label, fields, files, timeout=700):
    bnd = ("----MaskEdit" + uuid.uuid4().hex).encode()
    body = app.build_multipart(fields, files, bnd)
    req = urllib.request.Request(BASE + "/images/edits", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    req.add_header("Authorization", "Bearer " + KEY)
    print(f"\n--- {label} ---")
    print(f"    fields: { {k: (v[:60] + '...' if isinstance(v, str) and len(v) > 60 else v) for k, v in fields.items()} }")
    print(f"    parts : {sorted(files.keys())}")
    print(f"    bytes : {len(body):,}")
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as r:
            raw = r.read()
        print(f"    HTTP {r.status}  {len(raw):,} bytes")
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
            it = (d.get("data") or [{}])[0]
            if it.get("b64_json"):
                img = Image.open(io.BytesIO(__import__('base64').b64decode(it["b64_json"])))
                print(f"    >>> SUCCESS image {img.size}")
                return True
            if it.get("url"):
                print(f"    >>> SUCCESS url {it['url'][:90]}")
                return True
            print("    body:", raw.decode("utf-8", "replace")[:500])
        except Exception as e:
            print("    parse:", e, raw[:300])
        return False
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        print(f"    HTTP {e.code} ERROR")
        print("    " + txt[:900].replace("\n", "\n    "))
        return False
    except Exception as e:
        print(f"    TRANSPORT {type(e).__name__}: {e}")
        return False


# ---- build the app's real payloads --------------------------------------
tw, th = 1024, 1536
pad_mode = "crop"

# canvas mask: paint the background bands, protect the middle figure slab
mx = np.zeros((H, W, 4), np.uint8)
mx[150:1243, 230:640, 3] = 255
canvas_mask = Image.fromarray(mx, "RGBA")

vis_png, pad_paint = app.make_visual_mask(src, canvas_mask, tw, th, pad_mode, invert=False)
alpha_png = app.build_mask_alpha(pad_paint)
img_fit = app.normalise_to_size(src, tw, th, pad_mode)
ibuf = io.BytesIO(); img_fit.save(ibuf, "PNG", optimize=True)
image_png = ibuf.getvalue()
print(f"payload sizes: image {len(image_png):,}  visual-mask {len(vis_png):,}  alpha {len(alpha_png):,}")

PROMPT = ("替换背景为无任何可辨认物体的平滑灰绿渐变：低饱和灰绿与灰橄榄色，左亮右暗的柔和明暗过渡，"
          "四角略暗。背景干净无纹理：不要纸张颗粒、不要水渍斑点、不要云絮雾状、不要建筑或地标。")

# 1) the app's exact masked request
ok1 = run("MASKED request (what the app sends)",
          {"model": MODEL, "prompt": app.SCHEMA_PROMPT + PROMPT, "n": "1",
           "size": f"{tw}x{th}", "quality": "low"},
          {"image": ("image.png", image_png, "image/png"),
           "image[1]": ("mask_ref.png", vis_png, "image/png"),
           "mask": ("mask.png", alpha_png, "image/png")})

# 2) same but WITHOUT the undocumented `mask` part (the spec only lists image[])
ok2 = run("same, but no undocumented `mask` part",
          {"model": MODEL, "prompt": app.SCHEMA_PROMPT + PROMPT, "n": "1",
           "size": f"{tw}x{th}", "quality": "low"},
          {"image": ("image.png", image_png, "image/png"),
           "image[1]": ("mask_ref.png", vis_png, "image/png")})

# 3) minimal: image only, plain prompt
ok3 = run("image only, plain prompt",
          {"model": MODEL, "prompt": PROMPT, "n": "1",
           "size": f"{tw}x{th}", "quality": "low"},
          {"image": ("image.png", image_png, "image/png")})

# 4) quality/size pairing sanity: low + 1024x1024
ok4 = run("low + 1024x1024 (spec-legal pair)",
          {"model": MODEL, "prompt": "plain", "n": "1",
           "size": "1024x1024", "quality": "low"},
          {"image": ("image.png", image_png, "image/png")})

print("\n================ SUMMARY ================")
for i, ok in enumerate([ok1, ok2, ok3, ok4], 1):
    print(f"  variant {i}: {'OK' if ok else 'FAILED'}")
