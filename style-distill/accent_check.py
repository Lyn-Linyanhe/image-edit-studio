"""测签名元素：暖粉点缀(腮红/唇/道具) 与 头发主色。"""
import numpy as np
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
from PIL import Image
from pathlib import Path

paths = sorted(Path(_MANTU_ROOT_STR).iterdir())
print(f"{'file':10}{'accent hex':>12}{'share%':>8}{'sat':>6}  {'hair hex':>9}{'lum':>6}")
acc_all, hair_all = [], []
for p in paths:
    im = Image.open(p).convert("RGB").resize((600, 800), Image.LANCZOS)
    rgb = np.asarray(im, dtype=np.float32) / 255.0
    hsv = np.asarray(im.convert("HSV"), dtype=np.float32) / 255.0
    lum = rgb.mean(axis=2)
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]

    # 暖粉点缀：红/粉相 + 明显饱和
    warm = (((h >= 335) | (h <= 35)) & (s > 0.25) & (v > 0.6))
    accent = rgb[warm].mean(axis=0) if warm.sum() > 20 else None
    if accent is not None:
        acc_all.append(accent)
    ahex = "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in accent) if accent is not None else "-"

    # 发色 = 画面中偏暗且面积大的区域：lum 在 p10~p30 且排除红粉（皮肤）
    band = (lum > np.quantile(lum, 0.10)) & (lum < np.quantile(lum, 0.30)) & (~warm)
    hair = rgb[band].mean(axis=0)
    hair_all.append(hair)
    hhex = "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in hair)

    print(f"{p.name[:8]:10}{ahex:>12}{warm.mean()*100:8.3f}"
          f"{(s[warm].mean() if warm.sum() else 0):6.3f}  {hhex:>9}{hair.mean():6.3f}")

if acc_all:
    m = np.mean(acc_all, axis=0)
    print("\n全组暖粉点缀均值: #%02X%02X%02X" % tuple(int(round(c * 255)) for c in m))
m = np.mean(hair_all, axis=0)
print("全组发色均值:     #%02X%02X%02X" % tuple(int(round(c * 255)) for c in m))
