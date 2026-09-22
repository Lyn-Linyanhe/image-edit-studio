"""放大看蒙版区到底改了什么，并给出蒙版内的改动分布。

用"模型实际收到的裁切图"与输出做同坐标对照（两者都是 1024×1024），
裁出蒙版外接框 + 边距，左右并排放大 4 倍，另存对照图。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "compose" / "images"))
from mask_edit_app import normalise_to_size          # noqa: E402

TW = TH = 1024
IN = Path(sys.argv[1]) if len(sys.argv) > 3 else ROOT / "style-distill/round_snow/input/C_snow_169.png"
OUT = Path(sys.argv[2]) if len(sys.argv) > 3 else ROOT / "style-distill/round_snow/out_masktest2_1k.png"
MK = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "style-distill/round_snow/work/mask_ornament.png"
a = Image.open(IN).convert("RGB")
out = Image.open(OUT).convert("RGB")
m = Image.open(MK).convert("L")

fit = normalise_to_size(a, TW, TH, "crop")
fitm = normalise_to_size(m, TW, TH, "crop")
M = np.asarray(fitm.convert("L")) > 127

A = np.asarray(fit).astype(np.float32)
B = np.asarray(out.resize((TW, TH), Image.LANCZOS)).astype(np.float32)
d = np.abs(A - B).mean(axis=2)

ins = d[M]
print(f"  蒙版内像素 {M.sum():,}")
for thr in (5, 10, 30, 60, 120):
    print(f"    改动 >{thr:3d} 的像素：{(ins>thr).sum():7,d}  占蒙版 {(ins>thr).mean()*100:5.2f}%")
print(f"  蒙版内最大改动 {ins.max():.1f}   均值 {ins.mean():.2f}")
print(f"  蒙版外最大改动 {d[~M].max():.1f}   均值 {d[~M].mean():.4f}")
print(f"  全图（含蒙版）平均 {d.mean():.2f}")

ys, xs = np.where(M)
y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
pad = 60
box = (max(0, x0 - pad), max(0, y0 - pad), min(TW, x1 + pad), min(TH, y1 + pad))
print(f"  蒙版外接框 {box}  → 需改区域占全图 {M.mean()*100:.2f}%")

ca, cb = fit.crop(box), out.resize((TW, TH), Image.LANCZOS).crop(box)
Z = 3
ca = ca.resize((ca.width * Z, ca.height * Z), Image.NEAREST)
cb = cb.resize((cb.width * Z, cb.height * Z), Image.NEAREST)
sheet = Image.new("RGB", (ca.width * 2 + 24, ca.height + 34), (20, 22, 26))
sheet.paste(ca, (0, 34)); sheet.paste(cb, (ca.width + 24, 34))
dr = ImageDraw.Draw(sheet)
dr.text((6, 8), "LEFT = what the model received (red-marked region cropped away)", fill=(230, 230, 230))
dr.text((ca.width + 30, 8), "RIGHT = result", fill=(230, 230, 230))
p = ROOT / "style-distill/round_snow/work" / f"_zoom_{MK.stem}.png"
sheet.save(p)
print(f"  对照图已存 {p}  {sheet.size}")
