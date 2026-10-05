"""量化分析一组参考图的绘画风格（配色 / 明度 / 饱和度 / 笔触密度 / 留白）。

用法:
    python analyze_style.py <图片目录> [-o style_stats.json]

输出: JSON，含每张图指标 + 全组聚合（k-means 主色板、色调直方图、笔触密度等）。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# ---------------------------------------------------------------- 基础工具


def load_image(path: Path, max_side: int = 900) -> Image.Image:
    im = Image.open(path)
    im = im.convert("RGB")
    if max(im.size) > max_side:
        scale = max_side / max(im.size)
        im = im.resize(
            (max(1, round(im.width * scale)), max(1, round(im.height * scale))),
            Image.LANCZOS,
        )
    return im


# 注意: 不要用 PIL 的 convert("LAB")。实测它对 a*/b* 的处理不可靠:
#   纯白 (255,255,255) -> a*=b*=-128; 纯红 -> (a*,b*)=(-47,-58) 而正确值约 (+80,+67);
#   两个近乎相同的近白像素甚至给出 A=0 与 A=255。故自行实现 CIE Lab(D65), 并用已知值自检。
_XYZ_FROM_RGB = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)
_WHITE_D65 = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)
_KAPPA_EPS = (6.0 / 29.0) ** 3


def srgb_to_cielab(rgb: np.ndarray) -> np.ndarray:
    """rgb: (...,3) in 0..1 -> CIE Lab (D65)。返回 (...,3) = L*, a*, b*。"""
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = lin @ _XYZ_FROM_RGB.T
    t = xyz / _WHITE_D65
    f = np.where(t > _KAPPA_EPS, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def selftest_lab() -> None:
    """用 CIE 标准参考值校验 a*/b* 实现（容差 0.2）。"""
    cases = {
        (255, 0, 0): (53.24, 80.09, 67.20),
        (255, 255, 0): (97.14, -21.55, 94.48),
        (0, 0, 255): (32.30, 79.19, -107.86),
        (255, 255, 255): (100.0, 0.0, 0.0),
        (0, 0, 0): (0.0, 0.0, 0.0),
    }
    worst = 0.0
    for rgb255, expected in cases.items():
        got = srgb_to_cielab(np.array(rgb255, dtype=np.float64) / 255.0)
        dev = float(np.max(np.abs(got - np.array(expected))))
        worst = max(worst, dev)
        print(f"  rgb{rgb255} -> L*{got[0]:7.2f} a*{got[1]:7.2f} b*{got[2]:7.2f}"
              f"  (期望 {expected}, 偏差 {dev:.3f})")
    if worst > 0.2:
        raise SystemExit(f"CIE Lab 自检失败, 最大偏差 {worst:.3f} > 0.2")
    print(f"  CIE Lab 自检通过 (最大偏差 {worst:.3f})")


def to_arrays(im: Image.Image):
    rgb = np.asarray(im, dtype=np.float32) / 255.0
    hsv = np.asarray(im.convert("HSV"), dtype=np.float32) / 255.0
    lab = srgb_to_cielab(rgb.astype(np.float64))
    return rgb, hsv, lab


def hex_of(rgb01) -> str:
    r, g, b = (int(round(float(c) * 255)) for c in rgb01)
    return f"#{r:02X}{g:02X}{b:02X}"


def srgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    """rgb: (...,3) in 0..1 -> OKLab. 用于感知均匀的聚类与色差。"""
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    r, g, b = lin[..., 0], lin[..., 1], lin[..., 2]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack(
        [
            0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
        ],
        axis=-1,
    )


def kmeans_oklab(pixels: np.ndarray, k: int, iters: int = 40, seed: int = 7):
    """感知均匀空间里的 k-means。pixels: (N,3) 0..1 sRGB。返回 (中心sRGB, 占比)。"""
    data = srgb_to_oklab(pixels.astype(np.float64))
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(data), size=min(k, len(data)), replace=False)
    centers = data[idx].copy()
    labels = np.zeros(len(data), dtype=np.int64)
    for _ in range(iters):
        # (N,K) 距离
        d = ((data[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = d.argmin(axis=1)
        if np.array_equal(new_labels, labels) and _ > 0:
            labels = new_labels
            break
        labels = new_labels
        for j in range(len(centers)):
            sel = data[labels == j]
            if len(sel):
                centers[j] = sel.mean(axis=0)
    counts = np.bincount(labels, minlength=len(centers)).astype(np.float64)
    order = np.argsort(-counts)
    centers, counts = centers[order], counts[order]
    # OKLab -> sRGB
    out = []
    for c in centers:
        L, a, b = c
        l_ = L + 0.3963377774 * a + 0.2158037573 * b
        m_ = L - 0.1055613458 * a - 0.0638541728 * b
        s_ = L - 0.0894841775 * a - 1.2914855480 * b
        l3, m3, s3 = l_**3, m_**3, s_**3
        r = +4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
        g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
        bb = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3
        lin = np.clip([r, g, bb], 0, 1)
        srgb = np.where(
            lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055
        )
        out.append(np.clip(srgb, 0, 1))
    return np.stack(out), counts / counts.sum()


def hue_family_hist(hsv: np.ndarray, mask: np.ndarray) -> dict:
    """按色相家族统计非留白像素占比（用饱和度加权，避免灰线噪声主导）。"""
    families = {
        "red_pink": (330, 360),
        "orange_brown": (15, 45),
        "yellow": (45, 70),
        "green": (70, 165),
        "cyan_teal": (165, 200),
        "blue": (200, 250),
        "purple_violet": (250, 290),
        "magenta_pink": (290, 330),
    }
    # 红区跨 0 度，单独并入 red_pink
    h = (hsv[..., 0] * 360.0)[mask]
    s = hsv[..., 1][mask]
    out = {k: 0.0 for k in families}
    out["red_pink"] += float(s[(h < 15)].sum())
    total = float(s.sum()) or 1.0
    for name, (lo, hi) in families.items():
        sel = (h >= lo) & (h < hi)
        out[name] += float(s[sel].sum())
    return {k: round(v / total, 4) for k, v in out.items()}


def edge_density(gray: np.ndarray) -> float:
    """Sobel 梯度均值，近似线稿/笔触密度。"""
    g = gray.astype(np.float64)
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    mag = np.sqrt(gx**2 + gy**2)
    return float(mag.mean() * 255.0 / 4.0)


# ---------------------------------------------------------------- 单图分析


def analyze_one(path: Path) -> dict:
    im = load_image(path)
    rgb, hsv, lab = to_arrays(im)
    h, w = rgb.shape[:2]

    lum = rgb.mean(axis=2)
    # 留白（纸白）掩膜：三通道都接近白
    paper = (rgb[..., 0] > 0.94) & (rgb[..., 1] > 0.94) & (rgb[..., 2] > 0.94)
    content = ~paper
    content_ratio = float(content.mean())

    s_flat = hsv[..., 1][content]
    v_flat = hsv[..., 2][content]

    # 线稿色：最暗的 2% 像素
    thr = np.quantile(lum[content], 0.02) if content_any(content) else 0.0
    ink_mask = content & (lum <= thr)
    ink_rgb = rgb[ink_mask].mean(axis=0) if ink_mask.any() else np.zeros(3)

    # 水彩淡涂比例：内容像素里非常浅的着色（V 高、S 低）占比
    wash = content & (hsv[..., 1] < 0.12)
    wash_ratio = float(wash.sum() / max(1, content.sum()))

    stats = {
        "file": path.name,
        "size": [int(im.width), int(im.height)],
        "aspect": round(im.width / im.height, 4),
        "paper_white_ratio": round(1.0 - content_ratio, 4),
        "content_ratio": round(content_ratio, 4),
        "sat_mean_content": round(float(s_flat.mean()) if s_flat.size else 0.0, 4),
        "sat_p90_content": round(float(np.quantile(s_flat, 0.90)) if s_flat.size else 0.0, 4),
        "val_mean_content": round(float(v_flat.mean()) if v_flat.size else 0.0, 4),
        "val_std_content": round(float(v_flat.std()) if v_flat.size else 0.0, 4),
        "lum_mean": round(float(lum.mean()), 4),
        "lum_p05": round(float(np.quantile(lum, 0.05)), 4),
        "lum_p95": round(float(np.quantile(lum, 0.95)), 4),
        "contrast_range": round(float(np.quantile(lum, 0.95) - np.quantile(lum, 0.05)), 4),
        "lab_a_mean": round(float(lab[..., 1][content].mean()), 3),
        "lab_b_mean": round(float(lab[..., 2][content].mean()), 3),
        "warm_cool_index": round(float(lab[..., 2][content].mean()), 3),
        "ink_line_color": hex_of(ink_rgb),
        "ink_lum": round(float(ink_rgb.mean()), 4),
        "wash_ratio": round(wash_ratio, 4),
        "edge_density": round(edge_density(lum), 3),
        "hue_family": hue_family_hist(hsv, content),
    }
    return stats


def content_any(mask: np.ndarray) -> bool:
    return bool(mask.any())


# ---------------------------------------------------------------- 聚合


def aggregate(paths: list[Path], per_image: list[dict]) -> dict:
    samples = []
    all_rgb = []
    for p in paths:
        im = load_image(p, max_side=420)
        rgb, hsv, lab = to_arrays(im)
        paper = (rgb[..., 0] > 0.94) & (rgb[..., 1] > 0.94) & (rgb[..., 2] > 0.94)
        content = ~paper
        px = rgb[content]
        if len(px) > 4000:
            idx = np.random.default_rng(3).choice(len(px), 4000, replace=False)
            px = px[idx]
        samples.append(px)
        all_rgb.append(rgb)

    stacked = np.concatenate(samples, axis=0)
    centers, shares = kmeans_oklab(stacked, k=10, seed=11)
    palette = [
        {
            "hex": hex_of(c),
            "share": round(float(s), 4),
            "lum": round(float(np.dot(c, [0.2126, 0.7152, 0.0722])), 4),
            "role": None,
        }
        for c, s in zip(centers, shares)
    ]

    # 逐图主色（各 5 色），用于看单图偏色
    per_palette = {}
    for p, im_stats in zip(paths, per_image):
        im = load_image(p, max_side=380)
        rgb, hsv, lab = to_arrays(im)
        paper = (rgb[..., 0] > 0.94) & (rgb[..., 1] > 0.94) & (rgb[..., 2] > 0.94)
        px = rgb[~paper]
        if len(px) == 0:
            continue
        idx = np.random.default_rng(5).choice(len(px), min(2500, len(px)), replace=False)
        c, s = kmeans_oklab(px[idx], k=5, seed=5)
        per_palette[p.name] = [
            {"hex": hex_of(ci), "share": round(float(si), 3)} for ci, si in zip(c, s)
        ]

    def mean_of(key):
        vals = [s[key] for s in per_image]
        return round(float(np.mean(vals)), 4)

    fam_keys = per_image[0]["hue_family"].keys()
    fam_mean = {
        k: round(float(np.mean([s["hue_family"][k] for s in per_image])), 4)
        for k in fam_keys
    }
    fam_mean = dict(sorted(fam_mean.items(), key=lambda kv: -kv[1]))

    agg = {
        "image_count": len(paths),
        "aspect_all": sorted({tuple(s["size"]) for s in per_image}),
        "paper_white_ratio_mean": mean_of("paper_white_ratio"),
        "sat_mean_content_mean": mean_of("sat_mean_content"),
        "sat_p90_content_mean": mean_of("sat_p90_content"),
        "val_mean_content_mean": mean_of("val_mean_content"),
        "val_std_mean": mean_of("val_std_content"),
        "contrast_range_mean": mean_of("contrast_range"),
        "lum_p05_mean": mean_of("lum_p05"),
        "lum_p95_mean": mean_of("lum_p95"),
        "lab_b_mean_mean": mean_of("lab_b_mean"),
        "wash_ratio_mean": mean_of("wash_ratio"),
        "edge_density_mean": mean_of("edge_density"),
        "palette_top10": palette,
        "hue_family_mean": fam_mean,
        "per_image_palette": per_palette,
    }
    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", help="图片目录")
    ap.add_argument("-o", "--out", default="style_stats.json")
    ap.add_argument("--selftest", action="store_true", help="只校验 CIE Lab 实现")
    args = ap.parse_args()

    if args.selftest:
        print("CIE Lab 自检:")
        selftest_lab()
        return 0

    if not args.folder:
        ap.error("需要提供图片目录 (或使用 --selftest)")

    folder = Path(args.folder)
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in exts)
    if not paths:
        print(f"no images in {folder}", file=sys.stderr)
        return 1

    per_image = [analyze_one(p) for p in paths]
    result = {"folder": str(folder), "per_image": per_image, "aggregate": aggregate(paths, per_image)}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    a = result["aggregate"]
    print(f"images: {a['image_count']}  sizes: {a['aspect_all']}")
    print(f"paper_white={a['paper_white_ratio_mean']:.3f}  content_sat={a['sat_mean_content_mean']:.3f} (p90 {a['sat_p90_content_mean']:.3f})")
    print(f"val_mean={a['val_mean_content_mean']:.3f} val_std={a['val_std_mean']:.3f} contrast_range={a['contrast_range_mean']:.3f}")
    print(f"lum p05={a['lum_p05_mean']:.3f} p95={a['lum_p95_mean']:.3f}  b*={a['lab_b_mean_mean']:+.2f}  wash_ratio={a['wash_ratio_mean']:.3f}  edge={a['edge_density_mean']:.2f}")
    print("palette:")
    for c in a["palette_top10"]:
        print(f"  {c['hex']}  {c['share']*100:5.1f}%  lum={c['lum']:.3f}")
    print("hue families:", a["hue_family_mean"])
    print(f"-> {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
