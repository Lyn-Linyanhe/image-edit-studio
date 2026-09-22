"""把"保护区"分成「内部」与「边缘环」分别量。

目的：椭圆内均值 16.53 里，属于"内部真被重画"和"只是边缘接缝"的各占多少。
方法：用 MinFilter 腐蚀蒙版得到内部，环带 = 原蒙版 - 内部。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "compose" / "images"))
from mask_edit_app import normalise_to_size          # noqa: E402

TW = TH = 1024
a = Image.open(ROOT / "style-distill/round_snow/input/C_snow_169.png").convert("RGB")
out = Image.open(ROOT / "style-distill/round_snow/out_maskinvert_1k.png").convert("RGB")
m = Image.open(ROOT / "style-distill/round_snow/work/mask_face.png").convert("L")

fit = normalise_to_size(a, TW, TH, "crop")
fitm = normalise_to_size(m, TW, TH, "crop").convert("L")
hard = fitm.point(lambda v: 255 if v > 127 else 0)
R = 9
inner = hard.filter(ImageFilter.MinFilter(R * 2 + 1))       # 腐蚀：向内缩 R 像素
I = np.asarray(inner) > 127
H = np.asarray(hard) > 127
ring = H & ~I

d = np.abs(np.asarray(fit).astype(np.float32) -
           np.asarray(out.resize((TW, TH), Image.LANCZOS)).astype(np.float32)).mean(axis=2)

def stat(name, mask):
    if mask.sum() == 0:
        print(f"    {name}: 空"); return
    v = d[mask]
    print(f"    {name:14s} 像素 {mask.sum():7,d}  均值 {v.mean():6.2f}  中位 {np.median(v):6.2f}"
          f"  改动>30 占 {(v>30).mean()*100:5.1f}%  最大 {v.max():5.1f}")

print(f"  腐蚀半径 {R} px（把边缘 R 像素的接缝单独归类）")
stat("内部(保护核心)", I)
stat("边缘环(接缝)", ring)
stat("外部(可改区)", ~H)
print()
print(f"  内部里逐像素完全相同的比例：{(d[I] < 1).mean()*100:.1f}%")
print(f"  外部里逐像素完全相同的比例：{(d[~H] < 1).mean()*100:.1f}%")
