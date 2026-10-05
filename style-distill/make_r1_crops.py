"""放大输出 r1 的头部区域，核对花/星饰/发夹/眼睛。"""
from pathlib import Path
from PIL import Image

src = Path("style-distill/target/r1/output_r1.jpg")
out = Path("style-distill/target/r1/crops")
out.mkdir(parents=True, exist_ok=True)
im = Image.open(src).convert("RGB")
W, H = im.size
print("source", W, H)
regions = {
    "r1_head": (0.10, 0.02, 0.75, 0.40),
    "r1_eyes": (0.30, 0.14, 0.62, 0.32),
    "r1_choker_ear": (0.32, 0.24, 0.75, 0.58),
}
for name, (l, t, r, b) in regions.items():
    box = (int(l*W), int(t*H), int(r*W), int(b*H))
    c = im.crop(box)
    sc = min(3.0, 1300/max(c.size))
    if sc > 1:
        c = c.resize((round(c.width*sc), round(c.height*sc)), Image.LANCZOS)
    p = out/f"{name}.png"
    c.save(p)
    print(f"  {name}: {box} -> {c.size}")
