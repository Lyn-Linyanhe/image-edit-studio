"""Extract the real accent hues by clustering saturated pixels, not by guessing points.

Usage: python palette2.py <source-image>
"""
import sys
from collections import Counter

import numpy as np
from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB")
a = np.asarray(img).astype(int)
H, W = a.shape[:2]
mx = a.max(axis=2)
mn = a.min(axis=2)
sat = mx - mn                                   # crude chroma
value = mx

print(f"image {W}x{H}")


def cluster(mask, label, top=6):
    px = a[mask]
    if not len(px):
        print(f"  {label}: none")
        return
    q = (px // 24 * 24)
    c = Counter(map(tuple, q))
    print(f"  {label}: {len(px)} px")
    for (r, g, b), n in c.most_common(top):
        print(f"      #{r:02X}{g:02X}{b:02X}  {n / len(px) * 100:5.1f}%")


# strongly coloured = accents (eyes, gem, feather)
cluster((sat > 60) & (value > 80), "saturated accents (sat>60)")

# the blue family specifically
blue = (a[:, :, 2] - a[:, :, 0] > 40) & (a[:, :, 2] > 100)
cluster(blue, "blue family (B-R>40)")

# near-neutral bright = dress / hair highlight
cluster((sat < 14) & (value > 195), "bright neutrals (dress/hair lit)")

# dark = choker beadwork / line art
cluster((value < 70), "dark (choker/line)")

# olive-green background
olive = (a[:, :, 1] >= a[:, :, 2]) & (a[:, :, 1] > a[:, :, 0]) & (sat > 8) & (sat < 40)
cluster(olive, "olive background family")

# hair: left third, mid-brightness, low chroma
hair = (sat < 25) & (value > 120) & (value < 215)
cluster(hair, "hair body (low-chroma mid-bright)", top=8)
