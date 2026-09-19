"""核对图2(47EC)的姿态：头部朝向、视线、手与书的相对位置与画幅关系。"""
from pathlib import Path
from PIL import Image

src = Path(r"C:\Users\typ\Desktop\mantu\47EC32AC427193D005E9658AF8461F97.jpg")
out = Path("style-distill/target/pose_ref2")
out.mkdir(parents=True, exist_ok=True)
im = Image.open(src).convert("RGB")
W, H = im.size
print("source", W, H)

regions = {
    "p2_head_face": (0.05, 0.02, 0.85, 0.42),
    "p2_hand_book": (0.00, 0.38, 0.75, 0.85),
    "p2_torso_full": (0.00, 0.20, 1.00, 0.92),
}
for name, (l, t, r, b) in regions.items():
    box = (int(l * W), int(t * H), int(r * W), int(b * H))
    c = im.crop(box)
    sc = min(3.0, 1300 / max(c.size))
    if sc > 1:
        c = c.resize((round(c.width * sc), round(c.height * sc)), Image.LANCZOS)
    p = out / f"{name}.png"
    c.save(p)
    print(f"  {name}: {box} -> {c.size}")
