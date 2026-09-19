"""裁切放大目标图关键区域，用于逐项核对 PRESERVE 细节。"""
from pathlib import Path

from PIL import Image

src = Path("style-distill/target/target.png")
out = Path("style-distill/target/crops")
out.mkdir(parents=True, exist_ok=True)
im = Image.open(src).convert("RGB")
W, H = im.size
print("source", W, H)

# (名字, 左, 上, 右, 下) 用相对坐标
regions = {
    "01_face_eyes": (0.20, 0.16, 0.72, 0.42),
    "02_flower_feather": (0.55, 0.10, 1.00, 0.62),
    "03_choker_neck": (0.28, 0.36, 0.80, 0.62),
    "04_dress_lace": (0.00, 0.55, 0.62, 1.00),
    "05_bg_left": (0.00, 0.00, 0.30, 1.00),
    "06_bg_right": (0.72, 0.00, 1.00, 1.00),
    "07_hair_top": (0.30, 0.00, 0.85, 0.24),
}
for name, (l, t, r, b) in regions.items():
    box = (int(l * W), int(t * H), int(r * W), int(b * H))
    c = im.crop(box)
    scale = min(3.0, 1400 / max(c.size))
    if scale > 1:
        c = c.resize((round(c.width * scale), round(c.height * scale)), Image.LANCZOS)
    p = out / f"{name}.png"
    c.save(p)
    print(f"  {name}: {box} -> {c.size}")
