"""辨识点对比：目标图 vs 输出图（蓝像素、高饱和蓝、发区均值色、明暗）。

用法:
    python compare_identity.py                          # 默认对比 目标图 vs r1
    python compare_identity.py <目标图> <输出图> [更多输出图...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_TARGET = "style-distill/target/target.png"
DEFAULT_OUTPUTS = ["style-distill/target/r1/output_r1.jpg"]

# 达标参考（来自目标图实测）
REQ = {
    "vivid_blue_pct": (0.10, None),   # 高饱和蓝占比下限 %
    "blue_pct": (0.15, None),         # 蓝像素总量下限 %
    "hair_lum": (0.45, 0.65),         # 发区均值色明度区间
    "lum_mean": (0.60, 0.82),         # 内容明度均值区间（高调但不过曝）
    "lum_p05": (0.35, 0.62),          # P05 区间
}


def probe(path: str, label: str) -> dict:
    im = Image.open(path).convert("RGB")
    W, H = im.size
    rgb = np.asarray(im, dtype=np.float64) / 255.0
    hsv = np.asarray(im.convert("HSV"), dtype=np.float64) / 255.0
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    lum = rgb.mean(axis=2)

    blue = (h >= 190) & (h <= 260) & (s > 0.20)
    vivid = (h >= 185) & (h <= 265) & (s > 0.35)

    hair_hex, hair_lum = "-", float("nan")
    band = np.zeros_like(lum, bool)
    band[: int(0.30 * H)] = True
    m = band & (lum > np.quantile(lum[band], 0.45)) & (lum < np.quantile(lum[band], 0.92))
    if m.sum():
        c = rgb[m].mean(axis=0)
        hair_hex = "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in c)
        hair_lum = float(np.dot(c, [0.2126, 0.7152, 0.0722]))

    r = {
        "file": path,
        "size": f"{W}x{H}",
        "blue_pct": blue.mean() * 100,
        "vivid_blue_pct": vivid.mean() * 100,
        "blue_avg": ("#%02X%02X%02X" % tuple(int(round(x * 255)) for x in rgb[blue].mean(axis=0)))
        if blue.sum() else "-",
        "blue_sat": float(s[blue].mean()) if blue.sum() else 0.0,
        "hair_hex": hair_hex,
        "hair_lum": hair_lum,
        "lum_mean": float(lum.mean()),
        "lum_p05": float(np.quantile(lum, 0.05)),
        "lum_min": float(lum.min()),
        "contrast": float(np.quantile(lum, 0.95) - np.quantile(lum, 0.05)),
    }
    print(f"\n{'=' * 78}\n{label}  ({r['size']})")
    print(f"  蓝/青像素占比        {r['blue_pct']:8.3f}%   平均色 {r['blue_avg']}  饱和度 {r['blue_sat']:.3f}")
    print(f"  高饱和蓝(s>0.35)占比 {r['vivid_blue_pct']:8.3f}%")
    print(f"  上部发区均值色       {r['hair_hex']}   明度 {r['hair_lum']:.3f}")
    print(f"  明暗: 均值 {r['lum_mean']:.3f}  P05 {r['lum_p05']:.3f}  "
          f"最暗 {r['lum_min']:.3f}  对比跨度 {r['contrast']:.3f}")
    return r


def verdict(t: dict, o: dict) -> None:
    print(f"\n{'=' * 78}\n达标判定（对照目标图实测 / 风格组区间）")
    checks = [
        ("高饱和蓝占比 %", o["vivid_blue_pct"], REQ["vivid_blue_pct"][0], None,
         f"目标 {t['vivid_blue_pct']:.3f}%"),
        ("蓝像素总量 %", o["blue_pct"], REQ["blue_pct"][0], None,
         f"目标 {t['blue_pct']:.3f}%"),
        ("发区明度", o["hair_lum"], *REQ["hair_lum"], f"目标 {t['hair_lum']:.3f}"),
        ("明度均值", o["lum_mean"], *REQ["lum_mean"], f"目标 {t['lum_mean']:.3f}"),
        ("亮度 P05", o["lum_p05"], *REQ["lum_p05"], f"目标 {t['lum_p05']:.3f}"),
    ]
    bad = 0
    for name, val, lo, hi, note in checks:
        ok = (lo is None or val >= lo) and (hi is None or val <= hi)
        rng = f"[{lo if lo is not None else '-'}, {hi if hi is not None else '-'}]"
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<16} {val:8.3f}  要求 {rng:<14} ({note})")
        bad += 0 if ok else 1
    print(f"\n  {len(checks) - bad}/{len(checks)} 项通过")
    if bad:
        print("  提示: 发区明度过高=发色被漂白; 高饱和蓝为 0=眼睛/羽毛/宝石被褪色;")
        print("        P05 高于要求=明暗抬过头(过曝); 蓝像素总量偏低=蓝色辨识点丢失。")


def main() -> int:
    args = sys.argv[1:]
    if args:
        target = args[0]
        outs = args[1:] or DEFAULT_OUTPUTS
    else:
        target = DEFAULT_TARGET
        outs = DEFAULT_OUTPUTS

    t = probe(target, "目标图（应有的身份）")
    for p in outs:
        if not Path(p).exists():
            print(f"\n跳过（不存在）: {p}")
            continue
        o = probe(p, f"输出（{Path(p).name}）")
        verdict(t, o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
