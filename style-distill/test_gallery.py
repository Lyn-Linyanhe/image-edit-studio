"""重启本地图片服务并验收新加的 /gallery 画廊路由。

重启方式：走插件已注册的同源路由（POST /dsh-image-edit/stop → /ensure），
这样不用碰 `dsh web`（重启它会断开当前会话页面）。
验收三件事：① 画廊页能列出图片；② 图片字节能取到且类型正确；③ 目录穿越被拒。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

GUI = "http://127.0.0.1:3080"
LOCAL = "http://127.0.0.1:8000"


def req(url: str, method: str = "GET", timeout: int = 30):
    r = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "") if e.headers else ""
    except Exception as e:
        return -1, str(e).encode(), ""


print("1) 重启前探测 /gallery（旧进程应为 404）")
code, _, _ = req(LOCAL + "/gallery", timeout=5)
print(f"   HTTP {code}")

print("2) 通过插件路由重启本地服务")
code, body, _ = req(GUI + "/dsh-image-edit/stop", method="POST", timeout=20)
print(f"   /stop    HTTP {code}  {body[:120].decode('utf-8', 'replace')}")
code, body, _ = req(GUI + "/dsh-image-edit/ensure", method="POST", timeout=40)
try:
    payload = json.loads(body.decode("utf-8", "replace"))
except Exception:
    payload = {}
print(f"   /ensure  HTTP {code}  ok={payload.get('ok')} started={payload.get('started')} "
      f"waitedMs={payload.get('waitedMs')}  {str(payload.get('message', ''))[:120]}")

if not payload.get("ok"):
    print("   ！服务未起来，后续验收无法进行")
    raise SystemExit(1)
time.sleep(0.5)

print("3) 验收 /gallery 画廊页")
code, body, ctype = req(LOCAL + "/gallery", timeout=60)
text = body.decode("utf-8", "replace")
print(f"   HTTP {code}  {ctype}  {len(body)} B")
print(f"   含 round_arcade 条目：{'round_arcade' in text}")
print(f"   含 out_v2_r4_wink：{'out_v2_r4_wink' in text}")
print(f"   缩略图 <img> 数：{text.count('<img')}")

print("4) 验收图片字节接口")
sample = r"C:\Users\typ\Desktop\mantu\style-distill\round_arcade\out_v2_r4_wink.png"
q = urllib.parse.quote(sample)
code, body, ctype = req(f"{LOCAL}/gallery/img?p={q}", timeout=60)
print(f"   HTTP {code}  {ctype}  {len(body)} B（原图 2382819 B）")

print("5) 验收目录穿越防护（应 404）")
for bad in (r"C:\Windows\win.ini", r"C:\Users\typ\Desktop\mantu\README.md",
            r"C:\Users\typ\Desktop\mantu\..\..\Windows\win.ini"):
    c, b, _ = req(f"{LOCAL}/gallery/img?p={urllib.parse.quote(bad)}", timeout=10)
    print(f"   {bad[:52]:54s} HTTP {c}")
