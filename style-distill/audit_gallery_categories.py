"""重启服务，并用**模块自己的分类器**导出三类清单 + 成果桶拼版图，供人眼核对。

用模块自己的分类器（单一事实来源），避免"测试脚本自己复刻一套规则"的自证问题。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(".").resolve()
GUI = "http://127.0.0.1:3080"

# 1) 重启本地服务（加载新规则）
for path, method in ((GUI + "/dsh-image-edit/stop", "POST"), (GUI + "/dsh-image-edit/ensure", "POST")):
    r = urllib.request.Request(path, method=method)
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            print(f"  {path.rsplit('/', 1)[-1]:8s} ok={d.get('ok')}")
    except Exception as e:
        print(f"  {path.rsplit('/', 1)[-1]:8s} 失败 {type(e).__name__}: {e}")

# 2) 直接调用模块里的分类器
spec = importlib.util.spec_from_file_location("mea", ROOT / "compose/images/mask_edit_app.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
rows, counts = mod.gallery_select()
print(f"\n  页签计数：全部={counts['all']}  成果={counts['deliver']}  局部={counts['detail']}  过程={counts['process']}")

by = {"deliver": [], "detail": [], "process": []}
for r in rows:
    by[r["cat"]].append(r["rel"])

for cat, label in (("deliver", "成果"), ("detail", "局部")):
    print(f"\n  == {label} {len(by[cat])} 张 ==")
    for rel in sorted(by[cat]):
        print(f"     {rel}")

print(f"\n  == 过程 {len(by['process'])} 张（只列前 12 与目录分布）==")
for rel in sorted(by["process"])[:12]:
    print(f"     {rel}")
from collections import Counter                                     # noqa: E402
dirs = Counter("/".join(r.split("/")[:-1]) for r in by["process"])
print("     目录分布：")
for d, n in dirs.most_common(12):
    print(f"       {n:4d}  {d}")

# 3) 导出成果桶的拼版图（用分类器的结果，不是我手写清单）
out = ROOT / "style-distill/_probe/sheet_deliver_only.txt"
out.write_text("\n".join(sorted(by["deliver"])), encoding="utf-8")
print(f"\n  成果桶清单已落盘：{out}")
