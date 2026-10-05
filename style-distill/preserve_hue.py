"""色相保留后处理：把生成图的明暗结构 + 原图的色相/配色 合成。

铁律 A（只迁移手法、不迁移配色）在提示词层面不可靠——模型很容易把目标图的发色
换成基准图色板里的银灰/灰紫。这个脚本从像素层面把它变成保证：

    L（明暗结构/光影）  <- 生成图
    h（色相）           <- 原图     不因基准图改变
    C（彩度）           <- 原图 * sat_scale   （sat_scale=1.0 表示完全保留原图饱和度）

用法:
    python preserve_hue.py --style-output gen.png --original target.png -o fixed.png
    python preserve_hue.py --style-output gen.png --original target.png -o fixed.png --sat-scale 0.4
    python preserve_hue.py --selftest

设计取舍:
    sat_scale 默认 1.0（完全保留原图饱和度）——这是最保守、最贴合"不换配色"的档位。
    若要同时拿到 1A 的低饱和手法，把它调小；脚本会算出"要到达风格水平该给多少"。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_XYZ_FROM_RGB = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)
_WHITE_D65 = np.array([0.95047, 1.0, 1.08883], dtype=np.float64)
_KAPPA_EPS = (6.0 / 29.0) ** 3
_XYZ_FROM_LAB = np.linalg.inv(_XYZ_FROM_RGB)


def srgb_to_cielab(rgb: np.ndarray) -> np.ndarray:
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = lin @ _XYZ_FROM_RGB.T
    t = xyz / _WHITE_D65
    f = np.where(t > _KAPPA_EPS, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack(
        [116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])],
        axis=-1,
    )


def cielab_to_srgb(lab: np.ndarray) -> np.ndarray:
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0

    def finv(t):
        t3 = t**3
        return np.where(t3 > _KAPPA_EPS, t3, 3 * (6 / 29) ** 2 * (t - 4 / 29))

    xyz = np.stack([finv(fx), finv(fy), finv(fz)], axis=-1) * _WHITE_D65
    lin = xyz @ _XYZ_FROM_LAB.T
    lin = np.clip(lin, 0.0, 1.0)
    return np.clip(np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055), 0, 1)


def selftest() -> int:
    print("Lab 往返自检:")
    for rgb255 in [(255, 0, 0), (255, 255, 0), (0, 0, 255), (255, 255, 255), (0, 0, 0), (128, 90, 60)]:
        rgb = np.array(rgb255, dtype=np.float64) / 255.0
        back = cielab_to_srgb(srgb_to_cielab(rgb))
        dev = float(np.max(np.abs(back - rgb)) * 255)
        print(f"  rgb{rgb255} -> 往返偏差 {dev:.4f}/255")
        if dev > 0.5:
            print("  失败")
            return 1
    print("  往返自检通过")
    return 0


def content_stats(rgb: np.ndarray) -> dict:
    paper = (rgb[..., 0] > 0.94) & (rgb[..., 1] > 0.94) & (rgb[..., 2] > 0.94)
    lab = srgb_to_cielab(rgb)
    C = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    lum = rgb.mean(axis=2)
    sel = ~paper
    return {
        "paper_white_ratio": round(float(paper.mean()), 4),
        "lum_p05": round(float(np.quantile(lum, 0.05)), 4),
        "lum_min": round(float(lum.min()), 4),
        "lum_mean": round(float(lum.mean()), 4),
        "val_mean_content": round(float(lum[sel].mean()) if sel.any() else 0.0, 4),
        "sat_mean_content": round(float((C[sel] / 100.0).mean()) if sel.any() else 0.0, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--style-output", help="生成图（提供明暗结构 L）")
    ap.add_argument("--original", help="原目标图（提供色相 h 与彩度 C）")
    ap.add_argument("-o", "--out", default="hue_preserved.png")
    ap.add_argument("--sat-scale", type=float, default=1.0,
                    help="彩度倍率。1.0=完全保留原图饱和度(默认)；0.35 附近约等于本风格的 0.085 水平")
    ap.add_argument("--luma-blend", type=float, default=0.0,
                    help="明暗混合：0=全用生成图结构，1=全用原图结构")
    ap.add_argument("--chroma-blur", type=float, default=0.0,
                    help="色相/彩度的模糊半径(px)。生成图与原图几何有位移时调大(建议 3-8)可减少色渗")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.style_output or not args.original:
        ap.error("需要 --style-output 与 --original（或使用 --selftest）")

    gen = Image.open(args.style_output).convert("RGB")
    ori = Image.open(args.original).convert("RGB")
    if ori.size != gen.size:
        print(f"尺寸不同，把原图 {ori.size} 重采样到生成图 {gen.size}（几何有位移时请调 --chroma-blur）")
        ori = ori.resize(gen.size, Image.LANCZOS)

    gen_rgb = np.asarray(gen, dtype=np.float64) / 255.0
    ori_rgb = np.asarray(ori, dtype=np.float64) / 255.0

    gen_lab = srgb_to_cielab(gen_rgb)
    ori_lab = srgb_to_cielab(ori_rgb)

    # 色相与彩度取自原图（可选模糊以减少几何位移造成的色渗）
    a_src = ori_lab[..., 1].copy()
    b_src = ori_lab[..., 2].copy()
    if args.chroma_blur > 0:
        from PIL import ImageFilter

        r = float(args.chroma_blur)
        a_src = np.asarray(
            Image.fromarray(((a_src + 128) / 1.5).clip(0, 255).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(r)
            ),
            dtype=np.float64,
        ) * 1.5 - 128.0
        b_src = np.asarray(
            Image.fromarray(((b_src + 128) / 1.5).clip(0, 255).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(r)
            ),
            dtype=np.float64,
        ) * 1.5 - 128.0

    # 彩度按 sat_scale 缩放：方向(色相)保持不变，只改长度
    a_out = a_src * args.sat_scale
    b_out = b_src * args.sat_scale

    # 明暗取自生成图
    L_out = gen_lab[..., 0] * (1.0 - args.luma_blend) + ori_lab[..., 0] * args.luma_blend

    out_lab = np.stack([L_out, a_out, b_out], axis=-1)
    out_rgb = cielab_to_srgb(out_lab)
    out_img = Image.fromarray((out_rgb * 255.0 + 0.5).astype(np.uint8))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(out_path)

    print(f"\n-> {out_path.resolve()}")
    s_ori = content_stats(ori_rgb)
    s_out = content_stats(out_rgb)
    print(f"{'指标':<22}{'原图(色相来源)':>16}{'生成图(结构来源)':>18}{'输出':>10}")
    for k in s_ori:
        print(f"{k:<22}{s_ori[k]:>16}{content_stats(gen_rgb)[k]:>18}{s_out[k]:>10}")

    target = 0.085
    if s_ori["sat_mean_content"] > 0:
        need = target / s_ori["sat_mean_content"]
        print(f"\n原图内容饱和度 {s_ori['sat_mean_content']:.3f}；"
              f"若要压到本风格水平 {target}，需要 --sat-scale {need:.2f}")
    print("色相已按原图保留：输出中任一像素的色相 = 原图该位置的色相（未受生成图色板影响）。")
    print("注意：色相取自原图**同位置**像素，几何有位移时必须调大 --chroma-blur，否则会色渗。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
