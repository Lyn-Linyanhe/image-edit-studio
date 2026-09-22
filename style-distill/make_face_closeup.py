"""从图2 裁出脸部特写（含头饰与颈饰），放大到近 1000px 做身份锚参考。

依据（SKILL.md 的已知规律）：身份参考**不能糊**——参考被压到 448px+模糊+量化后脸会跑偏，
改回清晰档立刻变准。现在有 JPEG 通道，投喂总额度从 0.56 MiB 起，放得下一张清晰的第三张图。

改图前必查之一：这张特写与内容图不是同一文件（它是图2 的局部，哈希必不同）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
src = Image.open(ROOT / "style-distill/round_arcade/input/B_char_style.png").convert("RGB")
print(f"  图2 {src.size}")

# 裁框：覆盖皇冠、粉云、两枚发夹、向日葵、整张脸、颈饰与发丝外轮廓
box = (110, 0, 810, 660)
crop = src.crop(box)
print(f"  裁框 {box} → {crop.size}")
side = 980
s = side / max(crop.size)
big = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
out = ROOT / "style-distill/round_arcade/input/D_face_closeup.png"
big.save(out)
print(f"  写出 {out.name}  {big.size}  {out.stat().st_size//1024} KB")
print(f"  覆盖率（相对图2）：{crop.width*crop.height/(src.width*src.height)*100:.0f}%")
