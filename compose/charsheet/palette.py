"""Print a coarse colour histogram of the target so the sheet can quote real hexes.

Usage: python palette.py <source-image>
"""
import sys
from collections import Counter

from PIL import Image

HEXW = 16
img = Image.open(sys.argv[1]).convert("RGB")
img = img.resize((224, 333), Image.LANCZOS)          # downscale so groups merge

c = Counter()
for r, g, b in img.getdata():
    key = (r // HEXW * HEXW, g // HEXW * HEXW, b // HEXW * HEXW)
    c[key] += 1

total = 224 * 333
print(f"{'hex':>9}  {'share':>6}   rgb")
for (r, g, b), n in c.most_common(14):
    print(f"#{r:02X}{g:02X}{b:02X}  {n / total * 100:5.2f}%   ({r},{g},{b})")

# targeted probes: report the mean of a small patch at each named point
print("\nprobes (5x5 patch mean):")
PX = int(837 / 224)
PY = int(1243 / 333)
W = 224
H = 333


def probe(name, xf, yf):
    x, y = int(xf * W), int(yf * H)
    patch = [img.getpixel((min(W - 1, max(0, x + dx)), min(H - 1, max(0, y + dy))))
             for dx in range(-2, 3) for dy in range(-2, 3)]
    r = sum(p[0] for p in patch) // len(patch)
    g = sum(p[1] for p in patch) // len(patch)
    b = sum(p[2] for p in patch) // len(patch)
    print(f"  {name:22s} #{r:02X}{g:02X}{b:02X}  ({r},{g},{b})")


probe("hair lit (crown)", 0.42, 0.06)
probe("hair mid", 0.30, 0.20)
probe("hair shadow (left)", 0.14, 0.30)
probe("skin lit (shoulder)", 0.30, 0.72)
probe("skin shadow (neck)", 0.44, 0.50)
probe("eye iris", 0.345, 0.455)
probe("flower ornament", 0.78, 0.30)
probe("feather blue", 0.40, 0.55)
probe("gem cyan", 0.40, 0.68)
probe("choker black", 0.44, 0.60)
probe("dress white", 0.18, 0.80)
probe("background", 0.80, 0.10)
probe("background 2", 0.06, 0.05)
