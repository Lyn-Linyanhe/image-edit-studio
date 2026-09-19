"""Fetch the plugin bundle using the EXACT url the boot graph advertises.

The boot row is:
  {"id":"dsh-image-edit","url":"/plugins/??dsh-image-edit/client.js&rev=..."}
Note the `&rev=` (not `?rev=`): the combined-bundle route treats the whole
`??` list as the path and the revision as a separate query key. Fetching without
it 404s, which is what made the earlier probes look like a plugin failure.
"""
import re
import urllib.error
import urllib.request
from pathlib import Path

log = Path("boot-test.log").read_text(encoding="utf-8", errors="replace")
tok = (re.search(r"token=([A-Za-z0-9_\-]+)", log) or [None, ""])[1]
PORT = 8099

req = urllib.request.Request(f"http://127.0.0.1:{PORT}/?token={tok}")
with urllib.request.urlopen(req, timeout=25) as r:
    html = r.read().decode("utf-8", "replace")

# the bundle <script src> blocks the page actually loads
srcs = [m.group(1).replace("&amp;", "&") for m in re.finditer(r'<script src="([^"]+)"', html)]
print("bundle script srcs in the served page:")
for s in srcs:
    if "plugins" in s:
        print("   ", s)

rows = re.findall(r'\{"id":"dsh-image-edit"[^}]*\}', html)
print("\nboot row(s) for dsh-image-edit:")
for x in rows:
    print("   ", x)

target = None
for s in srcs:
    if "dsh-image-edit" in s:
        target = s
        break
if target is None and rows:
    m = re.search(r'"url":"([^"]+)"', rows[0])
    target = m.group(1).replace("&amp;", "&") if m else None

if not target:
    print("\nno bundle url found")
    raise SystemExit(1)

print(f"\nfetching: {target}")
for auth in (False, True):
    url = target if not auth else target + f"&token={tok}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = r.read()
            text = body.decode("utf-8", "replace")
            print(f"  auth={'yes' if auth else 'no ':3s} HTTP {r.status}  {len(body):,} bytes")
            if "dsh-image-edit" in text:
                for k in ["__ModuleLoader__", "exports.apply", "exports.inject",
                          "sidebar.footer.action", 'require("react")', "FooterAction"]:
                    print(f"       {'ok  ' if k in text else 'MISS'} {k}")
                n = len(re.findall(r"__ModuleLoader__\.load", text))
                print(f"       registrations in bundle: {n}")
            break
    except urllib.error.HTTPError as e:
        print(f"  auth={'yes' if auth else 'no ':3s} HTTP {e.code}")
    except Exception as e:
        print(f"  auth={'yes' if auth else 'no ':3s} {type(e).__name__}: {e}")
