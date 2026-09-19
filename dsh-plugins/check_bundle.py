"""Verify the plugin's client bundle is actually served by the test instance.

404 without auth is expected: the API has a browser-trust fence. This compares
our bundle against a shipped third-party bundle as a control, with and without
the boot token.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

log = Path("boot-test.log").read_text(encoding="utf-8", errors="replace")
m = re.search(r"token=([A-Za-z0-9_\-]+)", log)
tok = m.group(1) if m else ""
port = 8099
base = f"http://127.0.0.1:{port}/plugins/"

cases = [
    ("our plugin  (combo ??dsh-image-edit/client.js)", "??dsh-image-edit/client.js"),
    ("our plugin  (single dsh-image-edit/client.js)", "dsh-image-edit/client.js"),
    ("control: bad name (should 404)", "does-not-exist/client.js"),
]

for label, path in cases:
    for auth in (False, True):
        url = base + path + (f"?token={tok}" if auth else "")
        tag = "with token" if auth else "no token  "
        try:
            req = urllib.request.Request(url)
            if auth:
                req.add_header("Cookie", f"token={tok}")
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read()
                text = body.decode("utf-8", "replace")
                print(f"  {label:46s} {tag} -> HTTP {r.status}  {len(body):>8,} bytes")
                if "dsh-image-edit" in text:
                    for k in ["__ModuleLoader__", "exports.apply", "exports.inject",
                              "sidebar.footer.action", 'require("react")']:
                        print(f"        {'ok  ' if k in text else 'MISS'} {k}")
                break
        except urllib.error.HTTPError as e:
            print(f"  {label:46s} {tag} -> HTTP {e.code}")
        except Exception as e:
            print(f"  {label:46s} {tag} -> {type(e).__name__}: {e}")

# how the shipped bundles are referenced in the served HTML (for URL shape)
req = urllib.request.Request(f"http://127.0.0.1:{port}/?token={tok}")
with urllib.request.urlopen(req, timeout=25) as r:
    html = r.read().decode("utf-8", "replace")
print("\nsample script src from the served page:")
for mm in re.finditer(r'<script src="([^"]{0,180})"', html):
    src = mm.group(1)
    if "plugins" in src:
        print("   ", src[:170])
        break
print("\n__DSH_BOOT__ entry for our plugin:")
mm = re.search(r'\{"id":"dsh-image-edit".{0,400}', html)
if mm:
    print("   ", mm.group(0)[:400])
else:
    print("    not found")
