"""Isolate the content_policy_violation: is it this image, or the endpoint?

Trials, cheapest first:
  1. text-to-image only (no input image)          -> is generation allowed at all?
  2. edits with a synthetic, harmless image       -> does /images/edits work?
  3. edits with a near-empty prompt               -> is the PROMPT the trigger?
  4. edits with the user's image, plain prompt    -> is THIS IMAGE the trigger?
"""
import base64
import io
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask_edit_app as app

BASE = "https://image-direct.geiliapi.com/v1"
KEY = ""
MODEL = "gpt-image-2"
USER_IMG = "C:/Users/typ/Desktop/mantu/compose/base_v1.png"


def post_multipart(path, fields, files, timeout=600):
    bnd = ("----Probe" + uuid.uuid4().hex).encode()
    body = app.build_multipart(fields, files, bnd)
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


def verdict(st, txt):
    if st == 200:
        try:
            d = json.loads(txt)
            if (d.get("data") or [{}])[0].get("b64_json") or (d.get("data") or [{}])[0].get("url"):
                return "OK"
        except Exception:
            pass
        return "200 but no image"
    if "content_policy" in txt:
        return "CONTENT POLICY"
    if "deadline" in txt:
        return "UPSTREAM TIMEOUT"
    return f"HTTP {st}"


def png(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


def report(tag, st, txt):
    v = verdict(st, txt)
    print(f"  {tag:44s} -> {v}")
    if v not in ("OK",) and st != 200:
        msg = txt
        try:
            msg = json.loads(txt)["error"]["message"]
        except Exception:
            pass
        print(f"      {msg[:150]}")
    return v


print("=== 1. text-to-image (no input image) ===")
st, txt = post_json("/images/generations", {
    "model": MODEL, "prompt": "a simple gray-green abstract gradient background",
    "quality": "low", "size": "1024x1024", "n": 1})
report("generations, harmless prompt", st, txt)

print("\n=== 2. edits with a SYNTHETIC harmless image ===")
synth = Image.new("RGB", (900, 1350), (200, 190, 170))
for i in range(0, 1350, 90):
    for j in range(0, 900, 90):
        if (i // 90 + j // 90) % 2 == 0:
            synth.paste((120, 140, 120), (j, i, j + 90, i + 90))
synth_png = png(synth)
st, txt = post_multipart("/images/edits",
                         {"model": MODEL, "prompt": "make this a soft gray-green palette",
                          "n": "1", "size": "1024x1536", "quality": "low"},
                         {"image": ("image.png", synth_png, "image/png")})
report("edits, synthetic checker image", st, txt)

print("\n=== 3. edits with the USER image, minimal prompt ===")
u = Image.open(USER_IMG).convert("RGB")
fit = app.normalise_to_size(u, 1024, 1536, "crop")
u_png = png(fit)
for prompt in ["gray-green tones", "\u7070\u7eff\u8272\u8c03"]:
    st, txt = post_multipart("/images/edits",
                             {"model": MODEL, "prompt": prompt,
                              "n": "1", "size": "1024x1536", "quality": "low"},
                             {"image": ("image.png", u_png, "image/png")})
    report(f"edits, user image, prompt={prompt!r}", st, txt)
    time.sleep(1)

print("\n=== 4. edits with user image at a smaller size ===")
u_small = u.resize((512, 760))
st, txt = post_multipart("/images/edits",
                         {"model": MODEL, "prompt": "gray-green tones",
                          "n": "1", "size": "1024x1024", "quality": "low"},
                         {"image": ("image.png", png(u_small), "image/png")})
report("edits, user image downscaled 512x760", st, txt)

print("\n=== 5. generations with a description of the same subject ===")
st, txt = post_json("/images/generations", {
    "model": MODEL,
    "prompt": "an anime style girl with long pale ash-blonde hair and blue eyes, "
              "pale off-shoulder dress, muted gray-green palette, soft lighting",
    "quality": "low", "size": "1024x1536", "n": 1})
report("generations, describes the subject", st, txt)
