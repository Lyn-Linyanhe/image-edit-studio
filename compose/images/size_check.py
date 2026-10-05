"""Does the relay honour the requested `size` for gpt-image-2 edits?

Observed once: requested 1024x1024 but got 1254x1254. That call may have been a
late result of an earlier timed-out request, so re-measure with a clean call and
compare against the response's own width/height metadata fields.
"""
import base64
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 2)))
import io
import json
import ssl
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, ".")
import mask_edit_app as app
from PIL import Image

BASE = "https://image-direct.geiliapi.com/v1"
KEY = ""

src = Image.open(f"{_MANTU_ROOT_STR}/compose/input_red.jpg") \
    .convert("RGB").resize((1024, 1024))
b = io.BytesIO(); src.save(b, "PNG", optimize=True)
img = b.getvalue()

for size in ("1024x1024", "1024x1536"):
    print(f"--- request size={size}")
    bnd = ("----S" + uuid.uuid4().hex).encode()
    fields = {"model": "gpt-image-2",
              "prompt": "a plain gray-green abstract gradient, no objects",
              "n": "1", "size": size, "quality": "low"}
    body = app.build_multipart(fields, {"image": ("image.png", img, "image/png")}, bnd)
    r = urllib.request.Request(BASE + "/images/edits", data=body, method="POST")
    r.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    r.add_header("Authorization", "Bearer " + KEY)
    try:
        with urllib.request.urlopen(r, timeout=420,
                                    context=ssl.create_default_context()) as x:
            d = json.loads(x.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}: {e.read().decode('utf-8','replace')[:100]}")
        continue
    it = (d.get("data") or [{}])[0]
    meta = {k: it.get(k) for k in ("width", "height", "size_bytes", "mime_type")}
    print(f"    metadata: {meta}")
    raw = base64.b64decode(it["b64_json"])
    im = Image.open(io.BytesIO(raw))
    print(f"    actual image: {im.size}   b64 {len(raw)//1024} KB")
    ok = (f"{im.size[0]}x{im.size[1]}" == size)
    print(f"    honours requested size: {ok}")
