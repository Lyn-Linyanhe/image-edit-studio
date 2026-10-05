"""验证几个关键论断：是否真的没有纯黑；线稿颜色分布；留白比例；纯白像素纯度。"""
import json
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
from pathlib import Path

import numpy as np
from PIL import Image

paths = sorted(Path(_MANTU_ROOT_STR).iterdir())
rows = []
for p in paths:
    im = Image.open(p).convert("RGB").resize((600, 800), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32) / 255.0
    lum = a.mean(axis=2)
    flat = a.reshape(-1, 3)
    # 全局最暗像素
    idx = lum.reshape(-1).argmin()
    darkest = flat[idx]
    r, g, b = (int(round(c * 255)) for c in darkest)
    rows.append(
        {
            "file": p.name[:8],
            "lum_min": round(float(lum.min()), 3),
            "lum_p01": round(float(np.quantile(lum, 0.01)), 3),
            "darkest_hex": f"#{r:02X}{g:02X}{b:02X}",
            "pixels_below_0.2": round(float((lum < 0.20).mean()) * 100, 3),
            "pixels_below_0.35": round(float((lum < 0.35).mean()) * 100, 3),
            "pure_white_pct": round(float((a > 0.97).all(axis=2).mean()) * 100, 1),
        }
    )

print(f"{'file':10}{'min':>7}{'p01':>7}{'<0.20%':>9}{'<0.35%':>9}{'white%':>8}  darkest")
for r in rows:
    print(
        f"{r['file']:10}{r['lum_min']:7.3f}{r['lum_p01']:7.3f}"
        f"{r['pixels_below_0.2']:9.3f}{r['pixels_below_0.35']:9.3f}{r['pure_white_pct']:8.1f}  {r['darkest_hex']}"
    )

mins = [r["lum_min"] for r in rows]
print(f"\n全组最暗像素 min={min(mins):.3f}  max={max(mins):.3f}")
print(f"全组 <0.20 亮度像素占比 均值={np.mean([r['pixels_below_0.2'] for r in rows]):.4f}%")
print(f"全组纯白(>0.97)占比 均值={np.mean([r['pure_white_pct'] for r in rows]):.1f}%")
Path("style-distill/darkness_check.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
)
