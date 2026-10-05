"""调试：README 的 ✓ 判定为什么读不到。"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mea", ROOT / "compose/images/mask_edit_app.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

print(f"  GALLERY_REL_BASE = {m.GALLERY_REL_BASE}")
print(f"  常量检查：GALLERY_REL_BASE 在模块里 = {'GALLERY_REL_BASE' in dir(m)}")

for rel in ("style-distill/round_manga/out_v12B.png", "style-distill/round_manga/out_4kL_3840x2160.png",
            "style-distill/round_snow/out_A1_1k.png"):
    dirs = rel.split("/")[:-1]
    abs_round = os.path.join(m.GALLERY_REL_BASE, *dirs)
    print(f"\n  {rel}")
    print(f"    轮次绝对目录 = {abs_round}   存在={os.path.isdir(abs_round)}")
    print(f"    README 存在 = {os.path.isfile(os.path.join(abs_round, 'README.md'))}")
    acc = m._accepted_names(abs_round)
    print(f"    _accepted_names 返回 {len(acc)} 个：{sorted(acc)[:8]}")

readme = ROOT / "style-distill/round_manga/README.md"
lines = readme.read_text(encoding="utf-8").splitlines()
hit = [ln for ln in lines if "✓" in ln]
print(f"\n  round_manga/README.md 带 ✓ 的行数 = {len(hit)}")
if hit:
    print("  首行原文：")
    print("   ", hit[0][:120])
    print("  正则能抽出的名字：", re.findall(r"[A-Za-z0-9_\-]+\.(?:png|jpg|jpeg|webp|gif)", hit[0]))
