"""Which image endpoints does this relay actually expose?

Sends a deliberately malformed request to each candidate path. A 404 means the
route does not exist; 400/415/422 means it exists but the body was rejected.
"""
import json
import ssl
import urllib.error
import urllib.request

BASE = "https://image-direct.geiliapi.com/v1"
KEY = "sk-b692df77a0e6dc8920c399e501e30379b5452edf19efc588a51f128aa6f4d915"


def probe(path, method="POST", body=None, ctype="application/json"):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Bearer " + KEY)
    if body is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, data=body, timeout=60,
                                    context=ssl.create_default_context()) as r:
            return r.status, r.read().decode("utf-8", "replace")[:220]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:220]
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


cands = [
    ("GET",  "/models", None),
    ("POST", "/images/edits", b"{}"),
    ("POST", "/images/generations", b"{}"),
    ("POST", "/images/variations", b"{}"),
    ("POST", "/images/edit", b"{}"),
    ("POST", "/chat/completions", json.dumps(
        {"model": "gpt-image-2", "messages": [{"role": "user", "content": "hi"}]}).encode()),
]

print(f"{'METHOD':6s} {'PATH':24s} {'HTTP':>5s}  VERDICT")
print("-" * 78)
for method, path, body in cands:
    st, txt = probe(path, method, body)
    if st == 404:
        v = "route MISSING"
    elif st in (400, 415, 422):
        v = "route EXISTS (body invalid)"
    elif st == 401 or st == 403:
        v = "route EXISTS (auth)"
    elif st == 200:
        v = "route OK"
    elif st == -1:
        v = "request failed"
    else:
        v = "?"
    print(f"{method:6s} {path:24s} {st:>5}  {v}")
    if st not in (404, 200):
        print(f"        {txt[:150]}")
