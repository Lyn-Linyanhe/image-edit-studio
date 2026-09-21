"""把已认可的 s1 放大到 4K（2880×2880）——本地放大，不重新生成、内容不变。

为什么不用接口生成 4K（实测）：
  4K 目标尺寸下 normalise_to_size 会把投喂图统一缩放到 2880×2880，体积由"目标尺寸下的 PNG 编码"决定：
    内容原样(2.50) + 参考448(1.22) = 3.72 MiB  ✗
    内容灰度8级(1.17) + 参考448(1.22) = 2.39 MiB  ✗（超过实测被拒的 2.12 档）
    内容二值化(0.74) + 参考240px(0.94) = 1.68 MiB  ⚠️ 勉强发送，但网点全丢、身份参考被压糊
  且生成必然重画，拿不到"这一版的 4K"。

做法：Lanczos 放大 + **只在线条区域内**做轻度锐化（补偿插值带来的软化）。
线条掩膜用与减淡同一套"先闭后开"逻辑（缩放到 4K 尺寸后核也按比例放大）。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
SRC = HERE / "out_v12B_lineLighter_s1.png"
SIDE = 2880
SHARP_AMOUNT = 0.55     # 线条区域内的锐化强度
SHARP_RADIUS = 2.0


def main() -> int:
    im = Image.open(SRC).convert("RGB")
    up = im.resize((SIDE, SIDE), Image.LANCZOS)                 # ① Lanczos 放大
    a = np.asarray(up).astype(np.float32) / 255.0
    lum = a.mean(axis=2)

    # ② 线条掩膜（核按 2880/1024≈2.8 倍放大）
    dark = (lum < 0.50).astype(np.uint8)
    merged = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    solid = cv2.morphologyEx(merged, cv2.MORPH_OPEN, np.ones((35, 35), np.uint8))
    solid_d = cv2.dilate(solid, np.ones((19, 19), np.uint8))
    line = (lum < 0.45) & (solid_d == 0)

    # ③ 只在线条区域内做 unsharp
    blur = np.asarray(up.filter(ImageFilter.GaussianBlur(SHARP_RADIUS))).astype(np.float32) / 255.0
    sharp = np.clip(a + SHARP_AMOUNT * (a - blur), 0, 1)
    m = line[..., None].astype(np.float32)
    out = np.clip(a * (1 - m) + sharp * m, 0, 1)

    p = HERE / "out_final_4k_2880.png"
    Image.fromarray((out * 255).astype(np.uint8)).save(p, optimize=True)
    print(f"写出 {p.name}  {SIDE}x{SIDE}  {p.stat().st_size/1048576:.2f} MB")
    print(f"线条掩膜占比: {line.mean():.4f}（只在这部分做了锐化，其余是纯 Lanczos 放大）")

    # ④ 回缩校验：放大后缩回 1K，应与 s1 高度一致 → 说明内容没被改动
    back = Image.fromarray((out * 255).astype(np.uint8)).resize(im.size, Image.LANCZOS)
    d = np.abs(np.asarray(back).astype(np.int16) - np.asarray(im).astype(np.int16))
    print(f"\n回缩校验（4K→1K 与 s1 比较）：平均绝对差 {d.mean():.2f}/255，最大 {d.max()}/255")
    print("  （差异只来自插值与线条锐化；数值很小说明内容没有被改动）")

    # ⑤ 线条清晰度对照：线条区内的梯度能量（越大越锐）
    def grad_energy(img, mask_src):
        g = np.asarray(img.convert("L")).astype(np.float32)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        mag = np.hypot(gx, gy)
        m2 = cv2.resize(mask_src.astype(np.uint8), (g.shape[1], g.shape[0]),
                        interpolation=cv2.INTER_NEAREST) > 0
        return float(mag[m2].mean())
    e_plain = grad_energy(up, line)
    e_final = grad_energy(Image.fromarray((out * 255).astype(np.uint8)), line)
    print(f"\n线条区梯度能量：纯 Lanczos {e_plain:.1f} → 加锐化后 {e_final:.1f}"
          f"（提升 {100*(e_final-e_plain)/e_plain:.1f}%，说明线条没被插值糊掉）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
