"""Character-sheet crops: magnify regions of the target so details can be read.

Usage: python crop.py <source-image>
Writes zoomed PNGs into this directory.
"""
import os
import sys

from PIL import Image, ImageOps

OUT = os.path.dirname(os.path.abspath(__file__))


def zoom(img, box, target=1000):
    c = img.crop(box)
    s = max(1, round(target / max(c.width, c.height)))
    if s > 1:
        c = c.resize((c.width * s, c.height * s), Image.LANCZOS)
    return c


def main():
    src = sys.argv[1]
    img = Image.open(src).convert("RGB")
    W, H = img.size
    print(f"source {src}  {W}x{H}")

    # C1 full frame, normalised to square-ish for proportion reading
    img.resize((1000, round(1000 * H / W)), Image.LANCZOS).save(f"{OUT}/c1_full.png")

    # C2 head + ornaments (upper area)
    zoom(img, (int(W * 0.06), int(H * 0.00), int(W * 0.86), int(H * 0.34))).save(f"{OUT}/c2_head.png")

    # C3 flower ornament cluster
    zoom(img, (int(W * 0.18), int(H * 0.13), int(W * 0.56), int(H * 0.36)), 1000).save(f"{OUT}/c3_flower.png")

    # C4 neck / choker / jewellery
    zoom(img, (int(W * 0.34), int(H * 0.40), int(W * 0.86), int(H * 0.66)), 1000).save(f"{OUT}/c4_neck.png")

    # C5 dress / shoulder / lace
    zoom(img, (int(W * 0.10), int(H * 0.55), int(W * 0.88), int(H * 1.00)), 1000).save(f"{OUT}/c5_dress.png")

    # C6 face only, with a light grid for proportional measurement
    from PIL import ImageDraw
    fx0, fy0, fx1, fy1 = int(W * 0.30), int(H * 0.12), int(W * 0.80), int(H * 0.42)
    face = zoom(img, (fx0, fy0, fx1, fy1), 1000).convert("RGB")
    d = ImageDraw.Draw(face)
    step = face.width // 10
    for i in range(1, 10):
        d.line([(i * step, 0), (i * step, face.height)], fill=(255, 0, 0), width=1)
        d.line([(0, i * step), (face.width, i * step)], fill=(255, 0, 0), width=1)
    face.save(f"{OUT}/c6_face_grid.png")

    # C7 line-art only: kills colour so silhouette / line structure is readable
    g = ImageOps.autocontrast(img.convert("L"))
    zoom(g, (0, 0, W, H), 1000).save(f"{OUT}/c7_lineart.png")

    for f in sorted(os.listdir(OUT)):
        if f.endswith(".png"):
            print("  ", f, Image.open(f"{OUT}/{f}").size)


if __name__ == "__main__":
    main()
