"""Probe an OpenAI-compatible relay for gpt-image capability.

Usage:
    python probe_relay.py                 # uses defaults below
    python probe_relay.py <BASE_URL> <API_KEY>

Writes a result table to relay_probe.txt. The key is never printed in full.
"""
import json
import ssl
import sys
import urllib.error
import urllib.request

BASE_DEFAULT = "https://api.openai.com/v1"
KEY_DEFAULT = ""

BASE = (sys.argv[1] if len(sys.argv) > 1 else BASE_DEFAULT).rstrip("/")
KEY = sys.argv[2] if len(sys.argv) > 2 else KEY_DEFAULT


def mask_key(k: str) -> str:
    if not k:
        return "(empty)"
    return k[:8] + "..." + k[-4:] if len(k) > 14 else k[:4] + "..."


def req(url, method="GET", body=None, timeout=45):
    r = urllib.request.Request(url, method=method)
    r.add_header("Authorization", f"Bearer {KEY}")
    r.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode() if body is not None else None
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(r, data=data, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


lines = []
lines.append(f"BASE = {BASE}")
lines.append(f"KEY  = {mask_key(KEY)}")
lines.append("")

if not KEY:
    lines.append("!! No API key given. Pass it as the 2nd argument.")
    print("\n".join(lines))
    open("relay_probe.txt", "w", encoding="utf-8").write("\n".join(lines))
    sys.exit(1)

# 1) does the relay list models at all?
status, text = req(f"{BASE}/models")
lines.append(f"[GET /models] -> HTTP {status}")
image_models, all_models = [], []
if status == 200:
    try:
        j = json.loads(text)
        all_models = [m.get("id", "") for m in j.get("data", [])]
        image_models = [m for m in all_models
                        if any(t in m.lower() for t in
                               ("image", "dall", "gpt-image", "flux", "sd", "seedream", "kolors"))]
        lines.append(f"  total models: {len(all_models)}")
        lines.append(f"  image-ish models ({len(image_models)}):")
        for m in image_models[:60]:
            lines.append(f"    - {m}")
        if not image_models:
            lines.append("    (none matched image/dall/gpt-image/flux/sd/...)")
            lines.append("  first 25 models:")
            for m in all_models[:25]:
                lines.append(f"    - {m}")
    except Exception as e:
        lines.append(f"  (could not parse JSON: {e}) {text[:300]}")
else:
    lines.append(f"  {text[:400]}")

lines.append("")

# 2) which endpoints exist? POST with a minimal/bad body; 404 = route missing,
#    400/401/422 = route EXISTS. It returns an API error the key reveals nothing.
for path, body in [
    ("/images/generations", {"model": "gpt-image-1", "prompt": "x", "n": 1}),
    ("/images/edits", {"model": "gpt-image-1"}),
]:
    status, text = req(f"{BASE}{path}", "POST", body)
    verdict = "ROUTE EXISTS" if status in (400, 401, 403, 422, 500, 502) else (
        "NOT FOUND" if status == 404 else ("OK" if status == 200 else "?"))
    lines.append(f"[POST {path}] -> HTTP {status}  {verdict}")
    lines.append(f"  {text[:400]}")
    lines.append("")

open("relay_probe.txt", "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
