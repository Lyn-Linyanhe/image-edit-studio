"""测腮红/唇色（低饱和柔粉）与眼睛瞳孔色。"""
import numpy as np
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
from PIL import Image
from pathlib import Path

paths = sorted(Path(_MANTU_ROOT_STR).iterdir())
blush, pupil = [], []
print(f"{'file':10}{'blush hex':>11}{'share%':>8}{'sat':>6}{'val':>6}")
for p in paths:
    im = Image.open(p).convert("RGB").resize((600, 800), Image.LANCZOS)
    rgb = np.asarray(im, dtype=np.float32) / 255.0
    hsv = np.asarray(im.convert("HSV"), dtype=np.float32) / 255.0
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    warm = (((h >= 340) | (h <= 25)) & (s > 0.10) & (s < 0.30) & (v > 0.85))
    if warm.sum() > 30:
        blush.append(rgb[warm].mean(axis=0))
        c = "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in rgb[warm].mean(axis=0))
    else:
        c = "-"
    print(f"{p.name[:8]:10}{c:>11}{warm.mean()*100:8.3f}"
          f"{(s[warm].mean() if warm.sum() else 0):6.3f}{(v[warm].mean() if warm.sum() else 0):6.3f}")

if blush:
    m = np.mean(blush, axis=0)
    print("\n腮红/暖粉均值: #%02X%02X%02X" % tuple(int(round(x * 255)) for x in m))
