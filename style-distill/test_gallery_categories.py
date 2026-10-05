"""重启本地服务并验收画廊分类：每类数量、封顶行为、特定文件落在哪一类。

另外验证一件更要紧的事：**旧的交付件没有被上限挤掉**（round_manga 那批）。
"""
from __future__ import annotations

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
code, body = req(GUI + "/dsh-image-edit/stop", method="POST", timeout=20)
print(f"   /stop   HTTP {code}")
code, body = req(GUI + "/dsh-image-edit/ensure", method="POST", timeout=40)
try:
    payload = json.loads(body)
except Exception:
    payload = {}
print(f"   /ensure HTTP {code} ok={payload.get('ok')} started={payload.get('started')}")
if not payload.get("ok"):
    print("   ！服务未起来")
    raise SystemExit(1)

print("\n2) 取画廊页并统计分类")
code, page = req(LOCAL + "/gallery")
print(f"   HTTP {code}  {len(page)} 字")
cats = re.findall(r'data-cat="(deliver|detail|process)"', page)
from collections import Counter
counts = Counter(cats)
print(f"   卡片总数 {len(cats)}   成果 {counts['deliver']} / 局部 {counts['detail']} / 过程 {counts['process']}")
tabs = re.findall(r'class="tab[^"]*" data-cat="(\w+)">(\S+?)<span class="n">(\d+)</span>', page)
print("   页签上的计数：", [f"{t[1]}={t[2]}" for t in tabs])

print("\n3) 特定文件是否落在预期类别（按卡片块匹配，避免与页签的 data-cat 混淆）")
blocks = re.findall(r'<figure class="card" data-cat="(\w+)">(.*?)</figure>', page, re.S)
print(f"   解析出卡片 {len(blocks)} 个")
checks = [
    ("style-distill/round_arcade/out_v2_r4_wink.png", "deliver"),
    ("style-distill/round_manga/out_final_4k_2880.png", "deliver"),
    ("style-distill/round_snow/lab/out_r5c_repeat.redmark.png", "detail"),
    ("style-distill/round_snow/lab/out_r5c_primary.png", "detail"),
    ("style-distill/round_arcade/input/B_char_style.png", "process"),
    ("style-distill/round_snow/work/_zoom_mask_face.png", "detail"),
]
bad = 0
for rel, want in checks:
    got = None
    for cat, blk in blocks:
        if rel in blk:
            got = cat
            break
    mark = "OK " if got == want else "!! "
    if got != want:
        bad += 1
    print(f"   {mark} 期望 {want:8s} 实得 {str(got):8s} {rel}")
print(f"   → {'全部符合' if bad == 0 else str(bad) + ' 项不符'}")

print("\n4) 旧交付件有没有被挤掉（上限问题）")
for rel in ("round_manga/out_final_4k_2880.png", "round_manga/out_v16_uncompressed.png",
            "round_manga/out_color1.png"):
    print(f"   {'在' if rel in page else '缺失'}  {rel}")

print("\n5) 人眼入口")
print(f"   {LOCAL}/gallery")
