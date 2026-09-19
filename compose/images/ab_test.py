"""Clean A/B/C: multipart (the documented format) with and without a mask.

Earlier JSON-based runs were invalid (the endpoint answered with
"images[].image_url is required", i.e. it had switched to a different parsing
branch), so they proved nothing. This run uses only multipart/form-data.

A: 2nd reference image = a red/white VISUAL mask (what a VLM/LLM can read)
B: explicit `mask` field (undocumented; may be silently ignored)
C: image only + explicit "keep the rest" instruction  (control)

The base image deliberately has HARD half/half content so that "did the
protected region survive" is a numeric question, not a judgement call.
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
S = 1024


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


def edit(fields, files, timeout=700):
    bnd = ("----H" + uuid.uuid4().hex).encode()
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


def grab(text, tag):
    d = json.loads(text)
    it = (d.get("data") or [{}])[0]
    raw = None
    if it.get("b64_json"):
        raw = base64.b64decode(it["b64_json"])
    elif it.get("url"):
        with urllib.request.urlopen(it["url"], timeout=200,
                                    context=ssl.create_default_context()) as r:
            raw = r.read()
    if raw:
        open(f"_ab_{tag}.png", "wb").write(raw)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    return None


# base image: WHITE top (to be changed) / BLUE bottom (must survive)
a = np.zeros((S, S, 3), np.uint8)
a[: S // 2] = [245, 245, 245]
a[S // 2:] = [30, 60, 200]
ib = io.BytesIO(); Image.fromarray(a, "RGB").save(ib, "PNG", optimize=True)
image_png = ib.getvalue()

# visual mask: red where editable, white elsewhere (readable by the model)
mvis = np.full((S, S, 3), 255, np.uint8)
mvis[: S // 2] = [255, 0, 0]
mb = io.BytesIO(); Image.fromarray(mvis, "RGB").save(mb, "PNG", optimize=True)
mask_visual = mb.getvalue()

# alpha mask (OpenAI convention: transparent = editable)
mal = np.zeros((S, S, 4), np.uint8)
mal[: S // 2, :, 3] = 0
mal[S // 2:, :, 3] = 255
mb2 = io.BytesIO(); Image.fromarray(mal, "RGBA").save(mb2, "PNG", optimize=True)
mask_alpha = mb2.getvalue()

P_MASK = ("The second reference image is a mask. The red region marks the ONLY area to "
          "modify; every pixel outside it must remain exactly as in the first image. "
          "Replace the red region with flat orange.")
P_PLAIN = ("Replace only the white upper half with flat orange. "
           "Leave the blue lower half completely unchanged.")

runs = {
    "A_visual_mask_2nd_ref": (P_MASK,
        {"image": ("image.png", image_png, "image/png"),
         "image[1]": ("mask.png", mask_visual, "image/png")}),
    "B_alpha_mask_field": (P_MASK,
        {"image": ("image.png", image_png, "image/png"),
         "mask": ("mask.png", mask_alpha, "image/png")}),
    "C_control_prompt_only": (P_PLAIN,
        {"image": ("image.png", image_png, "image/png")}),
}

res = {}
for tag, (prompt, files) in runs.items():
    print(f"--- {tag} ---")
    st, txt = edit({"model": MODEL, "prompt": prompt, "quality": "low",
                    "size": "1024x1024", "n": "1"}, files)
    if st != 200:
        print(f"    HTTP {st}  {txt[:260]}\n")
        res[tag] = None
        continue
    im = grab(txt, tag)
    if im is None:
        print("    no image\n"); res[tag] = None; continue
    arr = np.asarray(im).astype(int)
    top = arr[: S // 2].reshape(-1, 3).mean(axis=0)
    bot = arr[S // 2:].reshape(-1, 3).mean(axis=0)

    # stronger metric: how much of the protected half is still blue-ish?
    b = arr[S // 2:]
    blue_frac = float(((b[:, :, 2] > 130) & (b[:, :, 0] < 120)).mean()) * 100
    # how much of the edit half actually changed to orange?
    t = arr[: S // 2]
    orange_frac = float(((t[:, :, 0] > 180) & (t[:, :, 1] > 60) & (t[:, :, 2] < 120)).mean()) * 100
    res[tag] = {"blue": blue_frac, "orange": orange_frac, "bot": bot, "top": top}
    print(f"    saved _ab_{tag}.png")
    print(f"    edit half turned orange : {orange_frac:5.1f}%   (want high)")
    print(f"    protected half still blue: {blue_frac:5.1f}%   (want high)")
    print()

print("=============== COMPARISON ===============")
for tag, r in res.items():
    if r:
        print(f"  {tag:26s} orange {r['orange']:5.1f}%   blue kept {r['blue']:5.1f}%")
    else:
        print(f"  {tag:26s} FAILED")
