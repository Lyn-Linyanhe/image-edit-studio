"""只把线稿调淡，其余像素不动（v3：用"先闭后开"识别网点填充的实心深块）。

两版失败教训：
  v1 直接对深色掩膜做开运算 → 网点点是"细"的，先被开掉了，**黑领结没被保护**，被一起调淡（s2 里领结灰掉）。
  v2 改用局部均暗来识别实心块 → **局部均暗分不开"网点填充的黑"与"密集排线"**
     （实测领结区 0.276，而误选的白衬衫采样框落在密排线上是 0.367），阈值取错、效果几乎消失。

v3 正解：**先闭后开**
  ① 取较宽的深色阈值（把网点点也算进来）；
  ② **闭运算**把小点连成实心块（领结因此成形，细线仍是细线）；
  ③ **开运算**用比线宽大得多的核把细线整条去掉，只留下实心块 → 这就是要保护的区域。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / "out_v12B.png"

T_DARK = 0.50      # ① 宽阈值：把网点小点也纳入
K_CLOSE = 5        # ② 闭运算：把点连成块
K_OPEN = 13        # ③ 开运算：比线宽大得多 → 只留实心块
T_LINE = 0.35      # 真正要调淡的"墨线"阈值（近黑）
LEVELS = [(0.20, "s1"), (0.34, "s2")]

PROBES = [
    ("黑领结(网点填充)", (400, 175, 505, 275)),
    ("白衬衫(纯线)    ", (380, 385, 470, 440)),
    ("裙子百褶(网点)  ", (330, 560, 420, 650)),
    ("头发排线(密线)  ", (200, 220, 280, 320)),
]


def main() -> int:
    im = Image.open(SRC).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a.mean(axis=2)

    dark = (lum < T_DARK).astype(np.uint8)
    merged = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((K_CLOSE, K_CLOSE), np.uint8))
    solid = cv2.morphologyEx(merged, cv2.MORPH_OPEN, np.ones((K_OPEN, K_OPEN), np.uint8))
    solid_d = cv2.dilate(solid, np.ones((7, 7), np.uint8))
    line = (lum < T_LINE) & (solid_d == 0)

    print(f"深色(lum<{T_DARK}) {dark.mean():.4f} → 闭后 {merged.mean():.4f} → 开后(实心块) {solid.mean():.4f}")
    print(f"实心深块占比（保护）: {solid.mean():.4f}")
    print(f"细线占比（要调淡）  : {line.mean():.4f}")
    print("\n采样框核对（该框内被判定为“实心块/被保护”的比例）：")
    for name, (x0, y0, x1, y1) in PROBES:
        frac = float(solid_d[y0:y1, x0:x1].mean())
        print(f"  {name} 被保护比例 = {frac:.3f}   （黑领结应高、纯线区应低）")

    vis = (a * 255).astype(np.uint8).copy()
    vis[solid_d > 0] = (0.45 * vis[solid_d > 0] + 0.55 * np.array([255, 0, 0])).astype(np.uint8)
    vis[line] = (0.45 * vis[line] + 0.55 * np.array([0, 90, 255])).astype(np.uint8)
    Image.fromarray(vis).save(HERE / "line_mask_preview.png")

    m = line[..., None]
    for alpha, tag in LEVELS:
        out = np.clip(a + (1.0 - a) * alpha * m, 0, 1)
        Image.fromarray((out * 255).astype(np.uint8)).save(
            HERE / f"out_v12B_lineLighter_{tag}.png", optimize=True)
        print(f"\n写出 out_v12B_lineLighter_{tag}.png (alpha={alpha})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
