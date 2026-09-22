"""确认浏览器刷新后会拿到**新版**客户端文件（含第二个按钮 image-gallery）。

做法：从 GUI 根页面里找出客户端模块表的引用方式，再直接取那段模块看内容。
"""
from __future__ import annotations

import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

GUI = "http://127.0.0.1:3080"


def get(url: str) -> tuple[int, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.headers.get("Content-Type", "")
    except Exception as e:
        return -1, str(e), ""


code, html, ctype = get(GUI + "/")
print(f"  GUI 根页面 HTTP {code}  {ctype}  {len(html)} 字")

refs = sorted(set(re.findall(r"[^\s\"'<>]*image-edit[^\s\"'<>]*", html)))
print(f"  页面里提到 image-edit 的 URL 片段（{len(refs)} 条）：")
for r in refs[:10]:
    print("   ", r[:130])

scripts = re.findall(r"<script[^>]+src=\"([^\"]+)\"", html)
print(f"  页面里的 <script src>（{len(scripts)} 条）：")
for s in scripts[:10]:
    print("   ", s[:130])

print("\n  客户端模块的实际地址是 /plugins/<id>/client.js（由 dsh-client-modules 以 prefix:/plugins 注册）：")
for cand in ("/plugins/dsh-image-edit/client.js",):
    c, body, ct = get(GUI + cand)
    flag = "含 image-gallery（新版）" if "image-gallery" in body else (
        "只有 image-edit（旧版）" if "image-edit" in body else "无标记")
    print(f"    {cand:38s} HTTP {c:4d}  {len(body):7d} B  {ct}  {flag}")
    if c == -1:
        print(f"      （取不到：{body[:80]}）")
