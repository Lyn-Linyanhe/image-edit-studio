"""Final proof: fetch the plugin bundle using the boot row's own url, with the
authenticated cookie jar, and verify its contents."""
import http.cookiejar
import re
import urllib.request
from pathlib import Path

log = Path("boot-test.log").read_text(encoding="utf-8", errors="replace")
tok = (re.search(r"token=([A-Za-z0-9_\-]+)", log) or [None, ""])[1]
ROOT = "http://127.0.0.1:8099"

jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
with op.open(f"{ROOT}/?token={tok}", timeout=25) as r:
    html = r.read().decode("utf-8", "replace")

row = re.search(r'\{"id":"dsh-image-edit"[^}]*\}', html)
url = re.search(r'"url":"([^"]+)"', row.group(0)).group(1).replace("&amp;", "&")
print("boot row url:", url)

with op.open(ROOT + url, timeout=45) as r:
    body = r.read()
    text = body.decode("utf-8", "replace")
    print(f"\nHTTP {r.status}   {len(body):,} bytes")
    for k in ["__ModuleLoader__", "dsh-image-edit", "exports.apply", "exports.inject",
              "sidebar.footer.action", 'require("react")', 'require("react/jsx-runtime")',
              "FooterAction", "jsxRuntime"]:
        print(f"   {'ok  ' if k in text else 'MISS'} {k}")
    n_self = len(re.findall(r"__ModuleLoader__\.load", text))
    ids = re.findall(r'id:\s*"([^"]+)"', text[:400])
    print(f"\n   registrations in this bundle: {n_self}")
    print(f"   id: {ids}")
    print("\n--- first 6 lines of the served bundle ---")
    for line in text.splitlines()[:6]:
        print("   " + line[:100])

# also confirm it appears in the combined bundle the page actually loads
print("\n--- combined bundle (what the page loads) ---")
combo = re.search(r'<script src="([^"]*dsh-image-edit[^"]*)"', html)
if combo:
    u = combo.group(1).replace("&amp;", "&")
    with op.open(ROOT + u, timeout=60) as r:
        t = r.read().decode("utf-8", "replace")
        print(f"   {u[:110]}")
        print(f"   HTTP {r.status}  {len(t):,} bytes  registrations: {len(re.findall('__ModuleLoader__.load', t))}")
        print(f"   contains dsh-image-edit: {'dsh-image-edit' in t}")
else:
    print("   combo src not matched by regex; raw snippet:")
    m = re.search(r'.{0,120}dsh-image-edit/client\.js.{0,120}', html)
    print("   ", m.group(0)[:240] if m else "not found")
