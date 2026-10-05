"""End-to-end smoke test for mask_edit_app.py using a local FAKE relay.

Verifies, without any real API key:
  - the app serves the UI
  - /api/ping and /api/models work
  - /api/edit parses multipart, letterboxes the image to an allowed size,
    rebuilds the mask in target coordinates, and forwards image+mask+prompt
  - the fake relay asserts the FORWARDED request really contains a mask part
    with the OpenAI convention (painted area transparent, rest opaque)
  - the returned b64 image is passed back to the caller
"""
import base64
import io
import json
import os
import sys
import threading
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask_edit_app as app  # noqa: E402

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("need Pillow+numpy")
    sys.exit(1)

RELAY_PORT = 18771
APP_PORT = 18772
captured = {}
FAILS = []


def safe(s):
    """Windows consoles are often GBK; never let printing kill the test."""
    enc = sys.stdout.encoding or "utf-8"
    return str(s).encode(enc, "replace").decode(enc, "replace")


def check(cond, label, detail=""):
    print(safe(("  PASS  " if cond else "  FAIL  ") + label +
               (f"  {detail}" if detail else "")))
    if not cond:
        FAILS.append(label)


class FakeRelay(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            body = json.dumps({"data": [{"id": "gpt-image-1"}, {"id": "gpt-4o"},
                                        {"id": "dall-e-3"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/images/edits"):
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        ctype = self.headers.get("Content-Type", "")
        body = self.rfile.read(n)
        captured["ctype"] = ctype
        captured["auth"] = self.headers.get("Authorization", "")
        bnd = ctype.split("boundary=", 1)[1].strip().strip('"').encode()
        fields, files = app.parse_multipart(body, bnd)
        captured["fields"] = fields
        captured["file_names"] = sorted(files.keys())

        # validate the mask semantics the app produced
        if "image[1]" in files:
            # the visual mask: the painted band must be flat RED in this reference
            v = np.asarray(Image.open(io.BytesIO(files["image[1]"][1])).convert("RGB")).astype(int)
            my = v.shape[0] // 2
            captured["vis_size"] = (v.shape[1], v.shape[0])
            captured["vis_band"] = v[my, 5].tolist()      # inside painted band
            captured["vis_centre"] = v[my, v.shape[1] // 2].tolist()  # untouched

        if "mask" in files:
            m = Image.open(io.BytesIO(files["mask"][1]))
            a = np.asarray(m.convert("RGBA"))
            alpha = a[:, :, 3]
            painted = (alpha == 0).sum()
            kept = (alpha == 255).sum()
            my = a.shape[0] // 2
            captured["mask_size"] = m.size
            captured["mask_painted_pct"] = float(painted) / alpha.size * 100
            captured["band_alpha"] = int(alpha[my, 5])
            captured["centre_alpha"] = int(alpha[my, a.shape[1] // 2])

        if "image" in files:
            im = Image.open(io.BytesIO(files["image"][1]))
            captured["image_size"] = im.size

        # reply with a recognisable synthetic image
        out = Image.new("RGB", (64, 64), (10, 200, 90))
        buf = io.BytesIO()
        out.save(buf, "PNG")
        payload = json.dumps({"data": [{"b64_json": base64.b64encode(buf.getvalue()).decode()}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


# ---------------- build a test image + canvas mask -------------------------
W, H = 900, 1330                      # deliberately NOT an allowed API size
test_img = Image.new("RGB", (W, H), (200, 120, 120))
test_img.save("_t_in.png")

# canvas mask: WHITE border band = "paint here = change here"; centre stays clear
mc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
mpx = np.zeros((H, W, 4), np.uint8)
mpx[:, :140] = [255, 255, 255, 255]          # left band painted
mpx[:, -140:] = [255, 255, 255, 255]         # right band painted
mc = Image.fromarray(mpx, "RGBA")
mc.save("_t_mask.png")


def post_multipart(url, fields, files):
    bnd = ("----T" + uuid.uuid4().hex).encode()
    body = app.build_multipart(
        fields,
        {k: (v[0], v[1], v[2]) for k, v in files.items()},
        bnd)
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode())


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.status, r.read()


relay = ThreadingHTTPServer(("127.0.0.1", RELAY_PORT), FakeRelay)
threading.Thread(target=relay.serve_forever, daemon=True).start()

appsrv = ThreadingHTTPServer(("127.0.0.1", APP_PORT), app.Handler)
threading.Thread(target=appsrv.serve_forever, daemon=True).start()

print("\n=== 1. UI served ===")
st, html = get(f"http://127.0.0.1:{APP_PORT}/")
check(st == 200, "GET / returns 200")
check(b"<canvas" in html and b"/api/edit" in html, "page contains canvas + edit endpoint")

print("\n=== 2. ping / models (these endpoints take JSON) ===")


def post_json(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode())


st, j = post_json(f"http://127.0.0.1:{APP_PORT}/api/ping",
                  {"base_url": f"http://127.0.0.1:{RELAY_PORT}/v1",
                   "api_key": "sk-test"})
check(j.get("ok") is True, "ping ok", str(j.get("message", "")).replace("\n", " ")[:70])

st, j = post_json(f"http://127.0.0.1:{APP_PORT}/api/models",
                  {"base_url": f"http://127.0.0.1:{RELAY_PORT}/v1",
                   "api_key": "sk-test"})
check(j.get("ok") is True, "models ok")
check("gpt-image-1" in j.get("image_models", []), "detects gpt-image-1",
      str(j.get("image_models")))

print("\n=== 3. edit round-trip ===")
img_bytes = open("_t_in.png", "rb").read()
mask_bytes = open("_t_mask.png", "rb").read()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    {"base_url": f"http://127.0.0.1:{RELAY_PORT}/v1",
     "api_key": "sk-test", "model": "gpt-image-1",
     "prompt": "smooth gray-green gradient background, no texture",
     "size": "1024x1536", "quality": "high",
     "pad_mode": "pad", "mask_mode": "std"},
    {"image_file": ("image.png", img_bytes, "image/png"),
     "mask_file": ("mask.png", mask_bytes, "image/png")},
)
check(j.get("ok") is True, "edit returned ok", str(j.get("message"))[:120])
check(bool(j.get("image_b64")), "returned image_b64 non-empty")

print("\n=== 4. what the relay actually received ===")
check(captured.get("file_names") == ["image", "image[1]", "mask"],
      "forwarded parts are image + image[1] + mask", str(captured.get("file_names")))
check(captured.get("fields", {}).get("prompt", "").startswith("[MASK INSTRUCTION]"),
      "mask instruction prepended to prompt",
      str(captured.get("fields", {}).get("prompt"))[:45])
check(captured.get("fields", {}).get("size") == "1024x1536",
      "size forwarded", str(captured.get("fields", {}).get("size")))
check(captured.get("auth") == "Bearer sk-test", "auth header forwarded",
      captured.get("auth", ""))
check(captured.get("image_size") == (1024, 1536),
      "image letterboxed to 1024x1536", str(captured.get("image_size")))
check(captured.get("mask_size") == (1024, 1536),
      "mask resized to 1024x1536", str(captured.get("mask_size")))
check(captured.get("vis_size") == (1024, 1536),
      "visual mask sized 1024x1536", str(captured.get("vis_size")))

# THE important one: the painted band must be red in the reference image
vb = captured.get("vis_band") or [0, 0, 0]
vc = captured.get("vis_centre") or [0, 0, 0]
check(vb[0] > 200 and vb[1] < 60 and vb[2] < 60,
      "painted region rendered FLAT RED in image[1] (relay's real mask mechanism)",
      f"band RGB={vb}")
check(vc[0] > 60 and abs(vc[0] - vc[1]) < 90,
      "unpainted region left as the original image (not red)",
      f"centre RGB={vc}")

pct = captured.get("mask_painted_pct", 0)
check(5 < pct < 45, "painted area plausible", f"{pct:.1f}% transparent")
check(captured.get("band_alpha") == 0,
      "alpha mask: painted -> alpha 0 (editable)",
      f"band alpha={captured.get('band_alpha')}")
check(captured.get("centre_alpha") == 255,
      "alpha mask: unpainted -> alpha 255 (protected)",
      f"centre alpha={captured.get('centre_alpha')}")

print("\n=== 5. inverse mask mode ===")
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    {"base_url": f"http://127.0.0.1:{RELAY_PORT}/v1",
     "api_key": "sk-test", "model": "gpt-image-1", "prompt": "x",
     "size": "1024x1536", "quality": "low", "pad_mode": "pad",
     "mask_mode": "inv"},
    {"image_file": ("image.png", img_bytes, "image/png"),
     "mask_file": ("mask.png", mask_bytes, "image/png")},
)
check(j.get("ok") is True, "inverse mode ok")
check(captured.get("band_alpha") == 255,
      "inverse flips the semantics (painted -> protected)",
      f"band alpha={captured.get('band_alpha')}")
check(captured.get("centre_alpha") == 0,
      "inverse: unpainted becomes editable",
      f"centre alpha={captured.get('centre_alpha')}")

print("\n=== 6. whole-image mode (no mask required) ===")
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    {"base_url": f"http://127.0.0.1:{RELAY_PORT}/v1", "api_key": "sk-test",
     "model": "gpt-image-1", "prompt": "restyle everything",
     "size": "1024x1536", "quality": "low", "pad_mode": "pad",
     "mask_mode": "std", "scope": "whole"},
    {"image_file": ("image.png", img_bytes, "image/png")},
)
check(j.get("ok") is True, "whole mode works WITHOUT any mask file",
      str(j.get("message"))[:100])
check(captured.get("file_names") == ["image"],
      "whole mode sends image only (no mask / no red reference)",
      str(captured.get("file_names")))
check(not str(captured.get("fields", {}).get("prompt", "")).startswith("[MASK INSTRUCTION]"),
      "whole mode does NOT prepend the mask instruction",
      str(captured.get("fields", {}).get("prompt"))[:40])
check(captured.get("image_size") == (1024, 1536),
      "whole mode still normalises the size", str(captured.get("image_size")))

print("\n=== 8. reference images (role-tagged) ===")
# Before this feature existed, a second uploaded image became a SECOND JOB and
# was never forwarded as a reference at all (server.log: parts == ['image_file']).
# These checks pin the new contract: refs are forwarded as image[1..] and the
# prompt carries an explicit slot map whose numbering matches what was sent.
ref_png = io.BytesIO()
Image.new("RGB", (300, 400), (30, 60, 200)).save(ref_png, "PNG")
ref_bytes = ref_png.getvalue()

FIELDS = {"base_url": f"http://127.0.0.1:{RELAY_PORT}/v1", "api_key": "sk-test",
          "model": "gpt-image-1", "prompt": "keep the face, change the style",
          "size": "1024x1536", "quality": "low"}

# --- 8a: whole mode + 2 refs -> image, image[1], image[2] ---
# English prompt, so the slot map must come out in English (language follows the
# user's prompt: _has_cjk()).
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    dict(FIELDS, scope="whole", ref_count="2",
         ref_roles=json.dumps(["style", "pose"])),
    {"image_file": ("image.png", img_bytes, "image/png"),
     "ref_file_0": ("ref1_style.png", ref_bytes, "image/png"),
     "ref_file_1": ("ref2_pose.png", ref_bytes, "image/png")},
)
check(j.get("ok") is True, "whole + 2 refs returns ok", str(j.get("message"))[:100])
check(captured.get("file_names") == ["image", "image[1]", "image[2]"],
      "whole mode forwards 2 refs as image[1] + image[2]",
      str(captured.get("file_names")))
p = captured.get("fields", {}).get("prompt", "")
check("Image 1 = CONTENT image to be edited" in p,
      "slot map (en): image 1 described as the content image", p[:80])
check("Image 2 = STYLE / TECHNIQUE reference" in p, "slot map (en): ref A labelled style")
check("Image 3 = POSE reference" in p, "slot map (en): ref B labelled pose")
check("do not infer roles from order" in p,
      "slot map warns the model not to infer roles from order")
check(p.rstrip().endswith("keep the face, change the style"),
      "user prompt stays last, after the slot map", p[-40:])
check(j.get("slot_map") and [s["index"] for s in j["slot_map"]] == [1, 2, 3],
      "response slot_map is 1,2,3", str(j.get("slot_map")))
check(j.get("parts_sent") == ["image", "image[1]", "image[2]"],
      "response reports the parts actually sent", str(j.get("parts_sent")))

# --- 8b: mask mode + 2 refs -> mask keeps image[1], refs shift to [2],[3] ---
# Chinese prompt here, to pin the slot map's language switching as well.
ref_bytes_cn = ref_bytes
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    dict(FIELDS, scope="mask", mask_mode="std", ref_count="2",
         ref_roles=json.dumps(["style", "pose"]),
         prompt="保持人物不变，只把画法改成水彩彩铅"),
    {"image_file": ("image.png", img_bytes, "image/png"),
     "mask_file": ("mask.png", mask_bytes, "image/png"),
     "ref_file_0": ("ref1_style.png", ref_bytes_cn, "image/png"),
     "ref_file_1": ("ref2_pose.png", ref_bytes_cn, "image/png")},
)
check(j.get("ok") is True, "mask + 2 refs returns ok", str(j.get("message"))[:100])
img_parts = [n for n in captured.get("file_names", []) if n == "image" or n.startswith("image[")]
check(img_parts == ["image", "image[1]", "image[2]", "image[3]"],
      "mask mode: refs shift to image[2] + image[3] (4 image parts)",
      str(captured.get("file_names")))
check("mask" in captured.get("file_names", []),
      "alpha mask part still sent alongside (relay ignores it, harmless)")
p = captured.get("fields", {}).get("prompt", "")
check(p.startswith("[MASK INSTRUCTION]"),
      "mask instruction still comes FIRST (verified contract preserved)", p[:40])
check("图1 = 要修改的内容图" in p, "slot map (zh): image 1 is the content image")
check("图2 = 红色标记图" in p, "slot map (zh): the red mask guide is 图2")
check("图3 = 画法 / 风格参考" in p, "slot map (zh): ref A labelled 画法/风格参考")
check("图4 = 姿态参考" in p, "slot map (zh): ref B labelled 姿态参考")
check(p.index("图2 = 红色标记图") < p.index("图3 = 画法"),
      "slot map numbers the red mask guide 图2 and refs from 图3")

# --- 8c: over the 4-part ceiling is refused, not silently truncated ---
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    dict(FIELDS, scope="mask", mask_mode="std", ref_count="3",
         ref_roles=json.dumps(["style", "pose", "other"])),
    {"image_file": ("image.png", img_bytes, "image/png"),
     "mask_file": ("mask.png", mask_bytes, "image/png"),
     "ref_file_0": ("r0.png", ref_bytes, "image/png"),
     "ref_file_1": ("r1.png", ref_bytes, "image/png"),
     "ref_file_2": ("r2.png", ref_bytes, "image/png")},
)
check(j.get("ok") is False, "mask + 3 refs (5 parts) is refused")
check("超出上限" in str(j.get("message", "")), "refusal explains the 4-image ceiling",
      str(j.get("message"))[:70])
check(captured.get("file_names") is None,
      "nothing was forwarded upstream when refused", str(captured.get("file_names")))

# --- 8d: engine without multi-image support is refused up front ---
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    dict(FIELDS, scope="whole", engine="grok", ref_count="1",
         ref_roles=json.dumps(["style"])),
    {"image_file": ("image.png", img_bytes, "image/png"),
     "ref_file_0": ("r0.png", ref_bytes, "image/png")},
)
check(j.get("ok") is False, "grok + reference image is refused (HTTP 400 upstream)")
check("不接受多张输入图片" in str(j.get("message", "")),
      "refusal names the engine limitation", str(j.get("message"))[:70])

# --- 8e: no refs -> behaviour identical to before the feature ---
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    dict(FIELDS, scope="whole", ref_count="0", ref_roles="[]"),
    {"image_file": ("image.png", img_bytes, "image/png")},
)
check(j.get("ok") is True, "no refs still works", str(j.get("message"))[:80])
check(captured.get("file_names") == ["image"],
      "no refs -> still just image", str(captured.get("file_names")))
_p = captured.get("fields", {}).get("prompt", "")
check("Image 2" not in _p,
      "no refs -> slot map lists only the content image", _p[:70])

# --- 8f: an unknown role degrades to 'other' instead of failing ---
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    dict(FIELDS, scope="whole", ref_count="1", ref_roles=json.dumps(["bogus"])),
    {"image_file": ("image.png", img_bytes, "image/png"),
     "ref_file_0": ("r0.png", ref_bytes, "image/png")},
)
check(j.get("ok") is True, "unknown role does not fail the run", str(j.get("message"))[:80])
_p = captured.get("fields", {}).get("prompt", "")
check("Image 2 = REFERENCE image" in _p,
      "unknown role falls back to the generic 'other' label", _p[:160])

print("\n=== 7. error handling ===")
captured.clear()
st, j = post_multipart(
    f"http://127.0.0.1:{APP_PORT}/api/edit",
    {"base_url": f"http://127.0.0.1:{RELAY_PORT}/v1", "api_key": "sk-test",
     "model": "gpt-image-1", "prompt": "x", "size": "1024x1536",
     "quality": "low", "pad_mode": "pad", "mask_mode": "std", "scope": "mask"},
    {"image_file": ("image.png", img_bytes, "image/png")},
)
check(j.get("ok") is False, "mask mode still rejects a missing mask",
      str(j.get("message"))[:60])

st, j = post_multipart(f"http://127.0.0.1:{APP_PORT}/api/ping",
                       {"base_url": "http://127.0.0.1:1/v1", "api_key": "k"}, {})
check(j.get("ok") is False and "message" in j, "bad base_url reported as failure")

for f in ("_t_in.png", "_t_mask.png"):
    try:
        os.remove(f)
    except OSError:
        pass

print("\n" + "=" * 60)
print("FAILED:", len(FAILS), FAILS if FAILS else "(all passed)")
print("=" * 60)
sys.exit(1 if FAILS else 0)
