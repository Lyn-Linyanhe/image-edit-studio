"""Is the 502 from the GPT edit transient or permanent? Retry it directly."""
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
GPT_KEY = ""
GROK_KEY = ""

src = Image.open("C:/Users/typ/Desktop/mantu/compose/input_red.jpg") \
    .convert("RGB").resize((1024, 1024))
b = io.BytesIO(); src.save(b, "PNG", optimize=True)
img = b.getvalue()

CASES = [
    ("gpt-image-2 / low + 1024x1024", GPT_KEY,
     {"model": "gpt-image-2", "prompt": "gray-green tones, keep the character",
      "n": "1", "size": "1024x1024", "quality": "low"}),
    ("gpt-image-2 / low + 1024x1536", GPT_KEY,
     {"model": "gpt-image-2", "prompt": "gray-green tones, keep the character",
      "n": "1", "size": "1024x1536", "quality": "low"}),
    ("gpt-image-2 / no quality field", GPT_KEY,
     {"model": "gpt-image-2", "prompt": "gray-green tones",
      "n": "1", "size": "1024x1024"}),
    ("grok-imagine-edit (control)", GROK_KEY,
     {"model": "grok-imagine-edit", "prompt": "gray-green tones",
      "n": "1", "size": "1024x1024", "resolution": "1k"}),
]

for label, key, fields in CASES:
    print(f"--- {label}")
    for attempt in (1, 2, 3):
        bnd = ("----R" + uuid.uuid4().hex).encode()
        body = app.build_multipart(fields,
                                   {"image": ("image.png", img, "image/png")}, bnd)
        r = urllib.request.Request(BASE + "/images/edits", data=body, method="POST")
        r.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
        r.add_header("Authorization", "Bearer " + key)
        try:
            with urllib.request.urlopen(r, timeout=420,
                                        context=ssl.create_default_context()) as x:
                t = x.read().decode("utf-8", "replace")
                it = (json.loads(t).get("data") or [{}])[0]
                print(f"    attempt {attempt}: HTTP {x.status}  keys={sorted(it.keys())}")
                break
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", "replace")
            print(f"    attempt {attempt}: HTTP {e.code}  {txt[:110]}")
        except Exception as e:
            print(f"    attempt {attempt}: {type(e).__name__}: {str(e)[:90]}")
