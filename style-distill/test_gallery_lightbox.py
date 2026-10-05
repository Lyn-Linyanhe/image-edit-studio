"""重启本地服务，验收页内灯箱：结构、无跳转、翻图与键盘、以及既有能力没被破坏。

注意：灯箱是浏览器行为，本脚本只能做**结构级**验证（标记与脚本在场、缩略图不再 target=_blank、
原图入口仍在、筛选与复制路径仍在）。真正的点击体验需要人眼一次。
"""
from __future__ import annotations
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))

import json
import re
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
GUI = "http://127.0.0.1:3080"
LOCAL = "http://127.0.0.1:8000"


def req(url, method="GET", timeout=60):
    r = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return -1, str(e)


print("1) 重启本地服务")
req(GUI + "/dsh-image-edit/stop", method="POST", timeout=20)
code, body = req(GUI + "/dsh-image-edit/ensure", method="POST", timeout=40)
try:
    payload = json.loads(body)
except Exception:
    payload = {}
print(f"   /ensure HTTP {code} ok={payload.get('ok')} started={payload.get('started')}")
if not payload.get("ok"):
    raise SystemExit("   ！服务未起来")

code, page = req(LOCAL + "/gallery")
print(f"\n2) 画廊页 HTTP {code}  {len(page)} 字")

def has(needle, label):
    ok = needle in page
    print(f"   {'OK ' if ok else '!! '} {label}")
    return ok

print("3) 结构检查")
has('<div id="lb" hidden>', "灯箱容器存在")
has('id="lb-img"', "灯箱大图元素存在")
has('id="lb-prev"', "上一张按钮存在")
has('id="lb-next"', "下一张按钮存在")
has('id="lb-close"', "关闭按钮存在")
has('id="lb-raw"', "「在新标签打开原图」入口仍在（想开原图时可用）")
has("ArrowRight", "键盘 ←/→ 支持存在")
has('Escape', "Esc 关闭支持存在")
has('lbImg.classList.toggle("zoom")', "点大图可切换 1:1 缩放")

print("4) 缩略图不再跳转（关键：不应再有 target=\"_blank\" 的缩略图链接）")
thumbs = re.findall(r'<figure class="card"[^>]*>(.*?)</figure>', page, re.S)
print(f"   卡片 {len(thumbs)} 个")
bad = [t for t in thumbs if 'target="_blank"' in t]
print(f"   {'OK ' if not bad else '!! '} 带 target=_blank 的卡片：{len(bad)} 个")
print(f"   {'OK ' if 'class="thumb"' in page else '!! '} 缩略图用 class=thumb（cursor:zoom-in，点击进灯箱）")

print("5) 既有能力未丢失")
has('id="q"', "搜索框仍在")
has('data-copy=', "每张卡片的「复制路径」仍在")
for cat, label in (('deliver', "成果"), ('detail', "局部"), ('process', "过程")):
    print(f"   {'OK ' if f'data-cat=\"{cat}\"' in page else '!! '} 分类页签 {label} 仍在")

print("\n6) 原图接口仍正常")
import urllib.parse                                          # noqa: E402
sample = rf"{_MANTU_ROOT_STR}\style-distill\round_arcade\out_v2_r4_wink.png"
try:
    with urllib.request.urlopen(
            f"{LOCAL}/gallery/img?p={urllib.parse.quote(sample)}", timeout=30) as r:
        print(f"   HTTP {r.status}  {r.headers.get('Content-Type')}  {len(r.read())} B")
except Exception as e:
    print(f"   !! {type(e).__name__}: {e}")

print(f"\n7) 人眼入口：{LOCAL}/gallery（刷新即可）")
