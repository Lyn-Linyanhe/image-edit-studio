"""验证：改过的客户端半边，浏览器现在能不能拿到（决定"刷新即可"还是"必须重启 dsh web"）。

dsh-client-modules 在启动时把客户端文件组合成内存副本（compose()），
之后只有 HMR 观察器调用 rebuilt(id) 才会更新。所以直接用浏览器会请求的那个
合并 URL 去取，看内容是新版还是旧版。
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
GUI = "http://127.0.0.1:3080"


def get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, f"<HTTP {e.code} {e.reason}>"
    except Exception as e:
        return -1, f"<{type(e).__name__}: {e}>"


cands = [
    "/plugins/image-edit/client.js",
    "/plugins/??image-edit/client.js",
    "/plugins/??image-edit/client.js&rev=0",
    "/plugins/image-edit/client.js.map",
    "/plugins/??dsh-image-edit/client.js",
    "/plugins/dsh-image-edit/client.js",
]
for c in cands:
    code, body = get(GUI + c)
    fresh = "image-gallery" in body
    old = ("image-edit" in body) and not fresh
    tag = "★新版（含 image-gallery）" if fresh else ("旧版（无 image-gallery）" if old else "无标记")
    print(f"  {c:44s} HTTP {code:4d}  {len(body):8d} B  {tag}")

# 同时看磁盘上的文件本身是不是新版（排除我写错文件）
from pathlib import Path                                    # noqa: E402
disk = Path("dsh-plugins/dsh-image-edit/lib/client.js").read_text(encoding="utf-8")
print(f"\n  磁盘文件：{len(disk)} 字  含 image-gallery={'image-gallery' in disk}")
