#!/usr/bin/env python3
"""体格报告：用轮廓宽度剖面自动量"头身比／肩宽比"——不再靠肉眼读网格。

为什么需要它：网格目测的误差约 ±1 头身，判不出 6.3 与 7.1 的差别，
而"身体幼态"正是要靠这个数来判定的。

原理（确定性，可复现）：
  1) 把画面二值化取出人物（黑白稿：人物＝深色像素，背景＝纸白）；
  2) 取最大连通域 → 人物的外接高度 H；
  3) 沿 y 求每一行的横向宽度 w(y)；
  4) **颈部 = 人物上段（顶部 8%–35%）内 w(y) 的极小值**（头与躯干之间最细处）；
  5) 头高 = 颈y − 顶y；**头身比 = H / 头高**；
  6) 头宽 = 顶到颈之间的最大宽度；肩宽 = 颈到颈+15%H 之间的最大宽度。

用法：
  python body_report.py --box 250,0,600,1024 img1.png --box 700,0,1420,1152 img2.png ...
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
from pathlib import Path

import numpy as np
from PIL import Image


def measure(path: Path, box: tuple[int, int, int, int]) -> dict | None:
    im = Image.open(path).convert("RGB").crop(box)
    a = np.asarray(im).astype(np.float32).mean(axis=2) / 255.0
    ink = a < 0.80                      # 深色＝人物（含较浅的网点）
    # 只保留最大的连通域（人物本体），去掉旁边的其它视图
    # （用 cv2 而不用 scipy.ndimage：本机没装 scipy，cv2 已在用）
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    if n <= 1:
        return None
    big = 1 + int(np.argmax(stats[1:, 4]))
    body = lab == big

    ys = np.where(body.any(axis=1))[0]
    if len(ys) < 50:
        return None
    top, bot = int(ys[0]), int(ys[-1])
    H = bot - top + 1
    w = body.sum(axis=1).astype(float)[top:bot + 1]

    lo, hi = int(0.08 * H), int(0.35 * H)
    if hi <= lo + 2:
        return None
    neck = lo + int(np.argmin(w[lo:hi]))
    head_h = neck                                  # top 已归零
    if head_h < 20:
        return None
    head_w = float(w[:neck].max())
    sh_lo, sh_hi = neck, min(len(w), neck + int(0.15 * H))
    shoulder_w = float(w[sh_lo:sh_hi].max()) if sh_hi > sh_lo else float("nan")

    return {
        "file": path.name,
        "crop": f"{box[0]},{box[1]},{box[2]},{box[3]}",
        "figure_h": H,
        "neck_y_pct": round(100 * neck / H, 1),
        "head_h": head_h,
        "heads_tall": round(H / head_h, 2),
        "head_w": int(head_w),
        "shoulder_w": int(shoulder_w),
        "shoulder_over_head_w": round(shoulder_w / head_w, 2) if head_w else float("nan"),
        "touches_bottom": bool(bot >= body.shape[0] - 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--box", action="append", required=True,
                    help="与 items 一一对应，格式 x0,y0,x1,y1（相对原图）")
    a = ap.parse_args()
    if len(a.box) != len(a.items):
        raise SystemExit("--box 个数必须与图片个数一致")

    print(f"{'文件':30s} {'图高px':>7s} {'颈在%':>6s} {'头高px':>7s} {'头身比':>7s} "
          f"{'头宽':>5s} {'肩宽':>5s} {'肩宽/头宽':>9s} {'底边贴边':>8s}")
    rows = []
    for item, bx in zip(a.items, a.box):
        box = tuple(int(v) for v in bx.split(","))
        r = measure(Path(item), box)  # type: ignore[arg-type]
        if not r:
            print(f"{Path(item).name:30s}   量不出来（人物没找到或裁框不对）")
            continue
        rows.append(r)
        print(f"{r['file']:30s} {r['figure_h']:7d} {r['neck_y_pct']:6.1f} {r['head_h']:7d} "
              f"{r['heads_tall']:7.2f} {r['head_w']:5d} {r['shoulder_w']:5d} "
              f"{r['shoulder_over_head_w']:9.2f} {'是(慎用)' if r['touches_bottom'] else '否':>8s}")
    print("\n判读：头身比越大越接近成人（青年女性约 7；幼儿约 5）。"
          "\n肩宽/头宽比越大越是成人（成人约 1.8–2.0；儿童约 1.2–1.4）。"
          "\n底边贴边=人物被裁框切到，头身比会偏小，该行不可用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
