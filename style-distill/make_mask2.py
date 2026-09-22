"""画第二个蒙版：落在她头发上（原图坐标系），供"涂哪改哪"的正面验证。

第一个蒙版（mask_ornament.png）事后看图才发现椭圆落在**空白天空**里，
不是发饰上——白跑了一次调用。所以这次先画、再本地预览 image[1]、确认无误才发送。

原图 1067×711，中心裁切后保留 x∈[178, 889]；椭圆要落在裁切后的画面里、且落在头发上。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
src = Image.open(ROOT / "style-distill/round_snow/input/C_snow_169.png")
print(f"  原图 {src.size}")

cx, cy, rx, ry = (int(v) for v in sys.argv[1:5]) if len(sys.argv) > 4 else (430, 250, 62, 48)
m = Image.new("L", src.size, 0)
ImageDraw.Draw(m).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
out = ROOT / "style-distill/round_snow/work/mask_hair.png"
m.save(out)
print(f"  椭圆中心 ({cx},{cy}) 半径 ({rx},{ry})  → {out.name}")
print(f"  覆盖率 {sum(m.getdata()) / 255 / (src.width * src.height) * 100:.2f}%")

# 裁切后是否落在取景范围内
crop_x0 = (src.width - int(src.height * 1.0)) // 2 if src.width / src.height > 1 else 0
print(f"  中心裁切起点 x={crop_x0} → 椭圆在裁切后画面内：{cx - rx > crop_x0}")
