"""Inspect the available assets: border/margin statistics and corner colors.

The bg of the 灰绿 reference is a soft gradient, so corner sampling tells us
whether an asset is the original (gray-green field) or a later high-key version.
"""
import numpy as np
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))
from PIL import Image

BASE = f"{_MANTU_ROOT_STR}/compose/"

for name in ["base_v1", "char_v2", "char_v3"]:
    im = Image.open(BASE + name + ".png").convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w, _ = a.shape
    print(f"--- {name}  {w}x{h}")

    # corners: 2% blocks
    m = max(4, int(min(w, h) * 0.02))
    corners = {
        "TL": a[:m, :m], "TR": a[:m, -m:],
        "BL": a[-m:, :m], "BR": a[-m:, -m:],
    }
    for k, blk in corners.items():
        c = blk.reshape(-1, 3).mean(axis=0)
        print(f"    {k}: R{c[0]:6.1f} G{c[1]:6.1f} B{c[2]:6.1f}  "
              f"sat={c.max()-c.min():5.1f}")

    # border ring stats = "how much of the frame is background-ish"
    ring = np.concatenate([
        a[:m].reshape(-1, 3), a[-m:].reshape(-1, 3),
        a[:, :m].reshape(-1, 3), a[:, -m:].reshape(-1, 3),
    ])
    print(f"    border mean: {ring.mean(axis=0).round(1)}  "
          f"std={ring.std(axis=0).round(1)}")
    print(f"    overall mean: {a.reshape(-1,3).mean(axis=0).round(1)}")
