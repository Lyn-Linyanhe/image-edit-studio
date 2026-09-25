"""Can we get the image as base64 instead of a URL we cannot download?

The relay returns `url` pointing at https://imgen.x.ai/... which this machine
cannot reach (TimeoutError 10060), so a URL-only response is unusable here.
Try the documented OpenAI-compatible switches that ask for inline data.
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
KEY = ""
PROMPT = "a quiet misty gray-green landscape, soft low contrast light"


def sj(path, obj, timeout=600):
    r = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(), method="POST")
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


variants = [
    ("plain (control)", {"model": "grok-imagine", "prompt": PROMPT, "n": 1,
                         "resolution": "1k", "size": "1024x1024"}),
    ("response_format=b64_json", {"model": "grok-imagine", "prompt": PROMPT, "n": 1,
                                  "resolution": "1k", "size": "1024x1024",
                                  "response_format": "b64_json"}),
    ("response_format=url", {"model": "grok-imagine", "prompt": PROMPT, "n": 1,
                             "resolution": "1k", "size": "1024x1024",
                             "response_format": "url"}),
    ("b64_json=true", {"model": "grok-imagine", "prompt": PROMPT, "n": 1,
                       "resolution": "1k", "size": "1024x1024", "b64_json": True}),
]

for tag, body in variants:
    st, txt = sj("/images/generations", body)
    if st != 200:
        print(f"  {tag:28s} HTTP {st}  {txt[:120]}")
        continue
    try:
        d = json.loads(txt)
    except Exception:
        print(f"  {tag:28s} HTTP 200 but not JSON: {txt[:120]}")
        continue
    it = (d.get("data") or [{}])[0]
    keys = sorted(it.keys())
    has_b64 = bool(it.get("b64_json"))
    url = it.get("url") or ""
    print(f"  {tag:28s} HTTP 200  keys={keys}  b64={'YES len=%d' % len(it['b64_json']) if has_b64 else 'no'}"
          f"  url={url[:60]}")
    if has_b64:
        raw = base64.b64decode(it["b64_json"])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        a = np.asarray(im).astype(np.float32)
        sat = (a.max(axis=2) - a.min(axis=2)).mean()
        print(f"      -> image {im.size}  {len(raw)//1024} KB  mean "
              f"{a.reshape(-1,3).mean(axis=0).round(0)}  sat {sat:.1f}")
        im.save("_grok_b64.png")
        print("      saved _grok_b64.png")

# also: can the relay itself proxy the download for us?
print("\n=== does the relay offer a proxy/download route? ===")
d = json.loads(sj("/images/generations", variants[0][1])[1])
u = (d.get("data") or [{}])[0].get("url", "")
print("  upstream url:", u[:110])
if u:
    for path in (f"/images/download?url={u}", f"/proxy?url={u}"):
        try:
            r = urllib.request.Request(BASE + path)
            r.add_header("Authorization", "Bearer " + KEY)
            with urllib.request.urlopen(r, timeout=60,
                                        context=ssl.create_default_context()) as x:
                b = x.read()
                print(f"  {path[:26]:28s} HTTP {x.status}  {len(b):,} bytes")
        except urllib.error.HTTPError as e:
            print(f"  {path[:26]:28s} HTTP {e.code}")
        except Exception as e:
            print(f"  {path[:26]:28s} {type(e).__name__}")
