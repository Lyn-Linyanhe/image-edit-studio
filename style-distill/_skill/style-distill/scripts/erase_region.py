#!/usr/bin/env python3
"""投喂前预处理：按多边形擦除目标图里"必须消失的东西"，并中和擦除痕迹。

为什么需要它（R5）：负向词删不掉图里已有的显著元素；但只擦掉还不够——
inpaint 会用周围颜色补底，若补出来的是"与某个身体部位同色"的平滑补丁，
模型会把它当成身体部位继续画下去。所以擦完必须再中和一次。

用法：
    python erase_region.py --src input.png --out clean.png \
        --poly "600,700 900,700 900,1100 600,1100" \
        [--poly "..."] [--dilate 8] [--radius 75] [--neutralize] [--preview]

    --poly 可给多个；坐标是原图像素，多边形顶点用空格分隔的 x,y。
    --neutralize  把擦除区降色度并往背景色拉（默认开启，除非显式 --no-neutralize）
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def load_polys(specs: list[str]) -> list[np.ndarray]:
    polys = []
    for s in specs:
        pts = []
        for pair in s.replace(";", " ").split():
            x, y = pair.split(",")
            pts.append([int(float(x)), int(float(y))])
        if len(pts) < 3:
            raise SystemExit(f"多边形顶点少于 3 个: {s}")
        polys.append(np.array(pts, np.int32))
    return polys


def background_color(rgb: np.ndarray, patch: int = 60) -> np.ndarray:
    h, w = rgb.shape[:2]
    samples = []
    for (x0, y0) in [(10, 10), (w - patch - 10, 10), (10, h - patch - 10), (w - patch - 10, h - patch - 10)]:
        samples.append(rgb[y0:y0 + patch, x0:x0 + patch].reshape(-1, 3).mean(axis=0))
    return np.mean(samples, axis=0)


def main() -> int:
    ap = argparse.ArgumentParser(description="按多边形擦除并中和擦除痕迹")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--poly", action="append", required=True, help='形如 "600,700 900,700 900,1100 600,1100"，可多次')
    ap.add_argument("--dilate", type=int, default=8)
    ap.add_argument("--radius", type=int, default=75)
    ap.add_argument("--neutralize", dest="neutralize", action="store_true", default=True)
    ap.add_argument("--no-neutralize", dest="neutralize", action="store_false")
    ap.add_argument("--feather", type=float, default=24.0, help="中和时的羽化半径")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()

    src = Path(a.src)
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)

    mask = np.zeros(rgb.shape[:2], np.uint8)
    for poly in load_polys(a.poly):
        cv2.fillPoly(mask, [poly], 255)
    if a.dilate:
        k = np.ones((a.dilate * 2 + 1, a.dilate * 2 + 1), np.uint8)
        mask = cv2.dilate(mask, k)

    cleaned = cv2.inpaint(rgb.astype(np.uint8), mask, a.radius, cv2.INPAINT_TELEA)
    cleaned = cv2.medianBlur(cleaned, 5).astype(np.float32)

    if a.neutralize:
        bg = background_color(rgb)
        soft = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), a.feather)
        soft = np.clip(soft * 1.6, 0, 1)[..., None]
        gray = cleaned.mean(axis=2, keepdims=True)
        desat = cleaned * 0.35 + gray * 0.65
        target = desat * 0.45 + bg.reshape(1, 1, 3) * 0.55
        cleaned = cleaned * (1 - soft) + target * soft
        print(f"  背景采样 RGB: {bg.round(1)}   已中和擦除区（降色度 + 往背景拉，羽化 {a.feather:.0f}px）")

    out = np.clip(cleaned, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(a.out)
    d = Path(a.out).parent
    Image.fromarray(mask).save(d / "mask.png")

    vis = (rgb * (1 - (mask > 0)[..., None]) + (mask > 0)[..., None] *
           (rgb * 0.45 + np.array([255, 0, 0]) * 0.55)).astype(np.uint8)
    Image.fromarray(vis).save(d / "mask_vis.png")

    print(f"  已写出 {a.out}（{out.shape[1]}x{out.shape[0]}）")
    print(f"  mask 覆盖 {int((mask > 0).sum())} px；同时写出 mask.png / mask_vis.png 供人工确认")
    if a.preview:
        Image.fromarray(out).save(d / "clean_preview.png")
    print("  ! 请务必打开 mask_vis.png 看一眼：多边形是否刚好框住要擦的东西，"
          "有没有多擦到头发、颈饰、衣服结构")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
