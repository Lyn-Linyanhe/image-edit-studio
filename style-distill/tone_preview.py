"""1A 明暗预览：只模拟 1A 的"抬暗部 + 压缩明暗 + 无黑"，不改色相、不加线稿。

用途：让"19.4% 的像素要被抬亮"这个代价在动手生成之前就看得见。
注意：这**不是**风格迁移结果——它不含笔触、线稿、水彩质感，只隔离出明暗这一项变化。
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from preserve_hue import cielab_to_srgb, srgb_to_cielab


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default="tone_preview.png")
    ap.add_argument("--floor", type=float, default=0.40, help="抬升后最暗值(0-1)，风格要求 >=0.35")
    ap.add_argument("--ceil", type=float, default=0.99, help="最亮值(0-1)")
    ap.add_argument("--split", type=float, default=0.5,
                    help="0-1，把明暗压向三档的强度：0=不动，1=完全压成三档")
    args = ap.parse_args()

    im = Image.open(args.src).convert("RGB")
    rgb = np.asarray(im, dtype=np.float64) / 255.0
    lab = srgb_to_cielab(rgb)
    L = lab[..., 0]

    before = {
        "lum_min": float(rgb.mean(axis=2).min()),
        "lum_p05": float(np.quantile(rgb.mean(axis=2), 0.05)),
        "lum_mean": float(rgb.mean()),
        "below_020": float((rgb.mean(axis=2) < 0.20).mean() * 100),
        "below_035": float((rgb.mean(axis=2) < 0.35).mean() * 100),
    }

    # 1) 线性把 L 区间压缩抬高：不产生黑，暗部整体上移
    lo, hi = args.floor * 100.0, args.ceil * 100.0
    L2 = lo + (L / 100.0) * (hi - lo)

    # 2) 可选的"压成三档"：向三个阶梯中心收敛（split 控制强度）
    if args.split > 0:
        steps = np.array([lo + 0.18 * (hi - lo), lo + 0.52 * (hi - lo), lo + 0.86 * (hi - lo)])
        idx = np.abs(L2[..., None] - steps[None, None, :]).argmin(axis=-1)
        L3 = steps[idx]
        L2 = L2 * (1 - args.split) + L3 * args.split

    out_lab = np.stack([L2, lab[..., 1], lab[..., 2]], axis=-1)  # 色相/彩度原封不动
    out_rgb = cielab_to_srgb(out_lab)
    out_img = Image.fromarray((out_rgb * 255 + 0.5).astype(np.uint8))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out_img.save(args.out)

    lum2 = out_rgb.mean(axis=2)
    after = {
        "lum_min": float(lum2.min()),
        "lum_p05": float(np.quantile(lum2, 0.05)),
        "lum_mean": float(lum2.mean()),
        "below_020": float((lum2 < 0.20).mean() * 100),
        "below_035": float((lum2 < 0.35).mean() * 100),
    }
    print(f"-> {Path(args.out).resolve()}")
    print(f"{'指标':<12}{'原图':>10}{'1A预览':>10}{'风格要求':>14}")
    req = {"lum_min": ">=0.15", "lum_p05": ">=0.35", "lum_mean": ">=0.60",
           "below_020": "~0", "below_035": "—"}
    for k in before:
        print(f"{k:<12}{before[k]:>10.3f}{after[k]:>10.3f}{req[k]:>14}")
    print("\n色相与彩度未改动（a*/b* 原样保留）；未添加笔触与线稿。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
