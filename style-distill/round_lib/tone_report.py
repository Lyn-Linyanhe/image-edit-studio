#!/usr/bin/env python3
"""只读的"调子剖面"验收工具。

把"画面深不深"变成可比的数：纸白占比 / 墨量 / 灰调 / 亮部 / 平均亮度 / 对比跨度 / 彩度。
用法：
    python tone_report.py <图...> [--ref <基准图>] [--json <输出路径>]
不带 --ref 时只打印表格；带 --ref 时按 5 个调子指标算"与基准的接近度"并排序（越小越接近）。

判读：深 = 墨量高、灰调高、纸白低、平均亮度低、对比跨度大。
"""
from __future__ import annotations
import sys as _sys
# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
# 这样不依赖 PYTHONIOENCODING 环境变量，也不会影响其它程序（见 SKILL.md 的「作业纪律」）。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

METRICS = ["paper", "ink", "mid", "light", "mean_lum", "range"]


def profile(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a.mean(axis=2)
    p = {
        "file": path.name,
        "size": f"{im.width}x{im.height}",
        "paper": float(((a[..., 0] > 0.94) & (a[..., 1] > 0.94) & (a[..., 2] > 0.94)).mean()),
        "ink": float((lum < 0.35).mean()),
        "mid": float(((lum >= 0.35) & (lum < 0.80)).mean()),
        "light": float((lum >= 0.80).mean()),
        "mean_lum": float(lum.mean()),
        "range": float(np.quantile(lum, 0.95) - np.quantile(lum, 0.05)),
    }
    lab = np.asarray(im.convert("LAB")).astype(np.int16)
    A = lab[..., 1].astype(np.float32)
    B = lab[..., 2].astype(np.float32)
    A = np.where(A > 127, A - 256, A)
    B = np.where(B > 127, B - 256, B)
    p["chroma"] = float(np.hypot(A, B).mean())
    return p


def closeness(p: dict, ref: dict) -> float:
    """与基准的接近度：5 个调子指标归一化绝对差之和，越小越接近。"""
    total = 0.0
    for k in METRICS:
        total += abs(p[k] - ref[k])
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description="调子剖面（只读）")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--ref", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    rows = [profile(Path(p)) for p in a.images]
    hdr = f"{'file':28s} {'纸白':>7s} {'墨量':>7s} {'灰调':>7s} {'亮部':>7s} {'平均亮度':>9s} {'对比跨度':>9s} {'彩度':>6s}"
    if a.ref:
        hdr += f" {'与基准距离':>11s}"
    print(hdr)
    ref = profile(Path(a.ref)) if a.ref else None
    out_rows = []
    for r in rows:
        line = (f"{r['file']:28s} {r['paper']:7.3f} {r['ink']:7.3f} {r['mid']:7.3f} "
                f"{r['light']:7.3f} {r['mean_lum']:9.3f} {r['range']:9.3f} {r['chroma']:6.1f}")
        if ref:
            d = closeness(r, ref)
            line += f" {d:11.3f}"
            out_rows.append((d, r))
        print(line)

    if ref:
        print(f"\n基准 {ref['file']}: 纸白{ref['paper']:.3f} 墨量{ref['ink']:.3f} "
              f"灰调{ref['mid']:.3f} 亮部{ref['light']:.3f} 平均亮度{ref['mean_lum']:.3f} 跨度{ref['range']:.3f}")
        print("\n按与基准的接近度排序（越小越接近）：")
        for i, (d, r) in enumerate(sorted(out_rows), 1):
            print(f"  {i}. {r['file']}   距离 {d:.3f}")
        print("  （第一个就是调子最接近基准的那一版）")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写出 {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
