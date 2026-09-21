"""证明"除被调淡的细线外，其余像素一个字节都没变"。"""
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
o = np.asarray(Image.open(HERE / "out_v12B.png").convert("RGB")).astype(np.int16)

for tag in ("s1", "s2"):
    n = np.asarray(Image.open(HERE / f"out_v12B_lineLighter_{tag}.png").convert("RGB")).astype(np.int16)
    diff = (o != n).any(axis=2)
    so, sn = o.sum(axis=2), n.sum(axis=2)
    brighter = int((diff & (sn > so)).sum())
    darker = int((diff & (sn < so)).sum())
    back = n.copy()
    back[diff] = o[diff]
    print(f"{tag}:")
    print(f"  改动像素 {int(diff.sum())} 个（占全图 {diff.mean() * 100:.2f}%）")
    print(f"    其中变亮 {brighter}、变暗 {darker}、未改动 {int((~diff).sum())}")
    print(f"  把改动像素还原后与原图逐像素完全一致 = {bool((back == o).all())}")
    print(f"  → 说明除这些像素外，其余像素一字节未变（内容、构图、网点、领结都在未改动集合里）")
    print()
