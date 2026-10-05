"""Work out how the token authenticates: capture the first response's headers
without following redirects, then reuse the cookie."""
import http.cookiejar
import re
import urllib.request
from pathlib import Path

log = Path("boot-test.log").read_text(encoding="utf-8", errors="replace")
tok = (re.search(r"token=([A-Za-z0-9_\-]+)", log) or [None, ""])[1]
PORT = 8099
ROOT = f"http://127.0.0.1:{PORT}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


op = urllib.request.build_opener(NoRedirect)
try:
    r = op.open(f"{ROOT}/?token={tok}", timeout=20)
    print("status:", r.status)
    for k, v in r.headers.items():
        print(f"  {k}: {v[:160]}")
except urllib.error.HTTPError as e:
    print("status:", e.code)
    for k, v in e.headers.items():
        print(f"  {k}: {v[:160]}")
    loc = e.headers.get("Location")
    if loc:
        print("  -> Location:", loc[:160])

print("\n--- retry with a cookie jar ---")
jar = http.cookiejar.CookieJar()
op2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
with op2.open(f"{ROOT}/?token={tok}", timeout=25) as r:
    html = r.read().decode("utf-8", "replace")
    print("page:", r.status, len(html), "bytes")
print("cookies:", [(c.name, c.value[:14]) for c in jar])

rows = re.findall(r'\{"id":"dsh-image-edit"[^}]*\}', html)
for x in rows:
    print("boot row:", x)
srcs = [m.group(1).replace("&amp;", "&") for m in re.finditer(r'<script src="([^"]+)"', html)
        if "dsh-image-edit" in m.group(1)]
print("bundle src:", srcs)

if srcs:
    with op2.open(ROOT + srcs[0], timeout=40) as r:
        body = r.read()
        text = body.decode("utf-8", "replace")
        print("\nbundle:", r.status, f"{len(body):,} bytes")
        for k in ["__ModuleLoader__", "exports.apply", "exports.inject",
                  "sidebar.footer.action", 'require("react")', "FooterAction"]:
            print(f"   {'ok  ' if k in text else 'MISS'} {k}")
