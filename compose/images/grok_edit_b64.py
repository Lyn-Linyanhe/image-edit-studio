"""Confirm image-to-image (grok-imagine-edit) also honours response_format=b64_json,
and that a single reference image is preserved reasonably."""
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
KEY = ""


def edit(fields, files, timeout=600):
    bnd = ("----G" + uuid.uuid4().hex).encode()
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
    r = urllib.request.Request(BASE + "/images/edits", data=bytes(out), method="POST")
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


def png(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


src = Image.open("C:/Users/typ/Desktop/mantu/compose/input_red.jpg").convert("RGB")
ref = src.resize((1024, 1024))
src_arr = np.asarray(ref).astype(np.float32)

cases = {
    "res=1k + b64": {"model": "grok-imagine-edit",
                     "prompt": "muted gray-green palette, keep composition and the character",
                     "resolution": "1k", "size": "1024x1024",
                     "response_format": "b64_json"},
    "res=2k + b64": {"model": "grok-imagine-edit",
                     "prompt": "muted gray-green palette, keep composition and the character",
                     "resolution": "2k", "size": "2048x2048",
                     "response_format": "b64_json"},
}

for tag, fields in cases.items():
    st, txt = edit(fields, {"image": ("image.png", png(ref), "image/png")})
    if st != 200:
        msg = txt
        try:
            msg = json.loads(txt)["error"]["message"]
        except Exception:
            pass
        print(f"  {tag:16s} HTTP {st}  {str(msg)[:140]}")
        continue
    d = json.loads(txt)
    it = (d.get("data") or [{}])[0]
    if not it.get("b64_json"):
        print(f"  {tag:16s} HTTP 200 but no b64: keys={sorted(it.keys())}")
        continue
    raw = base64.b64decode(it["b64_json"])
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    a = np.asarray(im.resize(ref.size)).astype(np.float32)
    diff = np.abs(a - src_arr).mean(axis=2)
    sat_src = (src_arr.max(axis=2) - src_arr.min(axis=2)).mean()
    sat_out = (a.max(axis=2) - a.min(axis=2)).mean()
    name = "_grok_edit_" + tag.split(" ")[0].replace("=", "") + ".png"
    im.save(name)
    print(f"  {tag:16s} HTTP 200  {im.size}  {len(raw)//1024} KB -> {name}")
    print(f"      input  mean {src_arr.reshape(-1,3).mean(axis=0).round(0)}  sat {sat_src:.1f}")
    print(f"      output mean {a.reshape(-1,3).mean(axis=0).round(0)}  sat {sat_out:.1f}"
          f"   (sat ratio {sat_out/max(sat_src,1e-6):.2f}x)")
    print(f"      mean abs diff vs input: {diff.mean():.1f}"
          f"   unchanged>88%: {(diff<12).mean()*100:.1f}%")
