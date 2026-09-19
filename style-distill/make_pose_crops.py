"""放大基准图 187D 的姿态区域：头部朝向、双手与书本的相对位置。"""
from pathlib import Path

from PIL import Image

src = Path(r"C:\Users\typ\Desktop\mantu\187DAFA40C9A79628386C5EE4F6966C4.jpg")
out = Path("style-distill/target/pose_ref")
out.mkdir(parents=True, exist_ok=True)
im = Image.open(src).convert("RGB")
W, H = im.size
print("source", W, H)

regions = {
    "pose_head": (0.15, 0.00, 0.95, 0.40),
    "pose_hands_book": (0.15, 0.42, 1.00, 0.95),
    "pose_torso": (0.00, 0.25, 1.00, 0.80),
}
for name, (l, t, r, b) in regions.items():
    box = (int(l * W), int(t * H), int(r * W), int(b * H))
    c = im.crop(box)
    scale = min(3.0, 1300 / max(c.size))
    if scale > 1:
        c = c.resize((round(c.width * scale), round(c.height * scale)), Image.LANCZOS)
    p = out / f"{name}.png"
    c.save(p)
    print(f"  {name}: {box} -> {c.size}")
