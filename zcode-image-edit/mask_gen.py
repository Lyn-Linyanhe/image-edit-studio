#!/usr/bin/env python3
"""区域规格 → 遮罩 PNG（本地确定性操作，不调接口）。

为什么需要它：`run_round.py --mask` 已经是可用的局部改图通道，但蒙版得有人画——
DSH 插件里是鼠标刷子，搬到 ZCode 后没有画布，所以这里把"刷子"换成**可编程的区域规格**：
矩形、多边形、种子点漫水、前景分割。代理据此生成蒙版，人手则仍可用 `zimage.py serve`
打开原来的网页来刷。

约定（与 `run_round.py build_with_mask` 完全一致，勿改）：
  · 输出 RGBA，**alpha=255 表示"你圈中的区域"**，其余 alpha=0；
  · 这个区域**是"要改"还是"要保护"，由调用方的 `--mask-invert` 决定**，本脚本不做反转——
    避免出现"蒙版反转了一次、调用方又反转一次"的对冲错误；
  · 蒙版坐标与**源图**同尺寸；`run_round` 会在尺寸不同时按内容图重采样，但同尺寸最稳。

自检：写出后完整解码；打印源图坐标下的区域占比，以及（给了 --preview 时）归一化到目标尺寸后
真正会被硬涂红的面积占比——后者才是 `run_round` 报的"可改面积"。
"""
from __future__ import annotations
import sys as _sys

# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import io
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

_HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- 区域构件

def _blank(h: int, w: int) -> np.ndarray:
    return np.zeros((h, w), bool)


def add_rect(region: np.ndarray, spec: str) -> None:
    """`x0,y0,x1,y1`，像素坐标，左闭右开；自动裁剪到画内。"""
    h, w = region.shape
    try:
        x0, y0, x1, y1 = (int(v) for v in spec.replace(" ", "").split(","))
    except Exception:
        raise SystemExit(f"--rect 格式应为 x0,y0,x1,y1，收到：{spec!r}")
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    x0, x1 = max(0, x0), min(w, x1)
    y0, y1 = max(0, y0), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        raise SystemExit(f"--rect {spec} 落在画外或为空（图 {w}x{h}）")
    region[y0:y1, x0:x1] = True


def add_polygon(region: np.ndarray, spec: str) -> None:
    """`x,y x,y x,y …`（至少 3 点）。"""
    pts = []
    for tok in spec.replace(",", " ").split():
        pts.append(float(tok))
    if len(pts) < 6 or len(pts) % 2:
        raise SystemExit(f"--polygon 需要成对的 x y 且至少 3 点，收到：{spec!r}")
    xy = list(zip(pts[0::2], pts[1::2]))
    h, w = region.shape
    layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(layer).polygon(xy, fill=255)
    region |= np.asarray(layer) > 127


def add_flood(region: np.ndarray, rgb: np.ndarray, spec: str) -> None:
    """`x,y[,tol]`：从种子点漫水填充颜色相近的连通区域。

    适合"把这片纯色/渐变背景换掉"——比给矩形精确得多，也比 grabcut 可预期。
    tol 是 cv2 的 loDiff/upDiff（每通道容差），默认 30。
    """
    parts = [p for p in spec.replace(" ", "").split(",") if p != ""]
    if len(parts) < 2:
        raise SystemExit(f"--flood 格式应为 x,y[,tol]，收到：{spec!r}")
    x, y = int(parts[0]), int(parts[1])
    tol = int(parts[2]) if len(parts) > 2 else 30
    h, w = region.shape
    if not (0 <= x < w and 0 <= y < h):
        raise SystemExit(f"--flood 种子点 ({x},{y}) 落在画外（图 {w}x{h}）")
    ff = np.zeros((h + 2, w + 2), np.uint8)
    flags = 4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8)
    cv2.floodFill(rgb.copy(), ff, (x, y), 0, (tol,) * 3, (tol,) * 3, flags)
    got = ff[1:-1, 1:-1] > 0
    if not got.any():
        raise SystemExit("--flood 一个像素都没填充到（种子点是否落在图上？）")
    region |= got


def add_grabcut(region: np.ndarray, rgb: np.ndarray, spec: str) -> None:
    """前景分割，取**前景**（不透明部分）。适合"只改主体"。

    未给矩形时按整图内缩 5% 作为初始框。**实测未做**：对动漫插画的效果不如漫水填充稳定，
    失败就退回 --flood / --polygon / 网页手涂。
    """
    h, w = region.shape
    if spec:
        x0, y0, x1, y1 = (int(v) for v in spec.replace(" ", "").split(","))
    else:
        mx, my = int(w * 0.05), int(h * 0.05)
        x0, y0, x1, y1 = mx, my, w - mx, h - my
    rect = (max(0, x0), max(0, y0), max(1, x1 - x0), max(1, y1 - y0))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gc = np.zeros((h, w), np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, gc, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    fg = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    if not fg.any():
        raise SystemExit("--grabcut 没分出前景（初始框是否覆盖到主体？）")
    region |= fg


def dilate(region: np.ndarray, px: int) -> np.ndarray:
    if px <= 0:
        return region
    k = np.ones((px * 2 + 1, px * 2 + 1), np.uint8)
    return cv2.dilate(region.astype(np.uint8), k, iterations=1) > 0


# ---------------------------------------------------------------- 产出

def to_rgba_png(region: np.ndarray) -> bytes:
    """alpha=255 在你圈中的区域；RGB 置白，便于当灰度图看也不会反。"""
    h, w = region.shape
    out = np.zeros((h, w, 4), np.uint8)
    out[..., 0:3] = 255
    out[..., 3] = np.where(region, 255, 0).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(out, "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="区域规格 → 遮罩 PNG（alpha=255 即你圈中的区域；改还是保由调用方决定）")
    ap.add_argument("--image", required=True, help="源图（遮罩与它同尺寸）")
    ap.add_argument("-o", "--out", required=True, help="输出遮罩 PNG")
    ap.add_argument("--rect", action="append", default=[],
                    help="x0,y0,x1,y1（可重复，取并集）")
    ap.add_argument("--polygon", action="append", default=[],
                    help="x,y x,y x,y …（可重复）")
    ap.add_argument("--flood", action="append", default=[],
                    help="x,y[,tol] 种子点漫水（可重复）")
    ap.add_argument("--grabcut", default=None, nargs="?", const="",
                    help="前景分割；可带初始框 x0,y0,x1,y1")
    ap.add_argument("--dilate", type=int, default=0, help="把区域外扩 N 像素（吃住抗锯齿边）")
    ap.add_argument("--preview", default="", help="另存一张「模型实际会收到的涂红图」用于肉眼核对")
    ap.add_argument("--size", default="1024x1536", help="预览用的目标尺寸")
    ap.add_argument("--pad", default="crop", choices=["pad", "crop"])
    a = ap.parse_args()

    src_p = Path(a.image)
    if not src_p.is_file():
        raise SystemExit(f"找不到源图：{src_p}")
    im = Image.open(src_p)
    im.load()                       # 完整解码：截断文件 open 不报错、只有 load 才报
    rgb = np.asarray(im.convert("RGB"))
    h, w = rgb.shape[:2]
    print(f"  源图 {src_p.name}  {w}x{h}")

    region = _blank(h, w)
    if a.rect:
        for s in a.rect:
            add_rect(region, s)
        print(f"  --rect ×{len(a.rect)}")
    if a.polygon:
        for s in a.polygon:
            add_polygon(region, s)
        print(f"  --polygon ×{len(a.polygon)}")
    if a.flood:
        for s in a.flood:
            add_flood(region, rgb, s)
        print(f"  --flood ×{len(a.flood)}  （种子点漫水）")
    if a.grabcut is not None:
        add_grabcut(region, rgb, a.grabcut)
        print("  --grabcut（前景分割；【未实测】对插画可能不稳）")

    if not region.any():
        raise SystemExit("没有给出任何区域：请用 --rect / --polygon / --flood / --grabcut 之一")
    if a.dilate:
        before = region.sum()
        region = dilate(region, a.dilate)
        print(f"  --dilate {a.dilate}px：{before} → {region.sum()} 像素")

    raw = int(region.sum())
    print(f"  区域面积 {raw} / {h * w} 像素 = {raw / (h * w) * 100:.1f}%（源图坐标）")

    out_p = Path(a.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    png = to_rgba_png(region)
    out_p.write_bytes(png)
    chk = Image.open(out_p)
    chk.load()
    print(f"  写出 {out_p}  {len(png):,} B  {chk.size} {chk.mode}  ✓ 完整可解码")

    if a.preview:
        # 用接口真用的那条路径算出"会被硬涂红"的图，确保预览与实发完全一致
        sys.path.insert(0, str(_HERE.parent / "compose" / "images"))
        from mask_edit_app import make_visual_mask  # noqa: E402
        tw, th = (int(v) for v in a.size.split("x"))
        cm = Image.fromarray(np.dstack([np.full((h, w), 255, np.uint8)] * 3 +
                                       [np.where(region, 255, 0).astype(np.uint8)]), "RGBA")
        vis, pad_paint = make_visual_mask(im.convert("RGB"), cm, tw, th, a.pad, invert=False)
        pv = Path(a.preview)
        pv.parent.mkdir(parents=True, exist_ok=True)
        pv.write_bytes(vis)
        Image.open(pv).load()
        print(f"  预览（模型实际会收到的 image[1]）{pv}  {tw}x{th}  "
              f"{len(vis):,} B  ✓ 完整可解码")
        print(f"  归一化到 {a.size} / pad={a.pad} 后的**可改面积** "
              f"{pad_paint.mean() * 100:.1f}%  ← run_round 会报的就是这个数")
        if not pad_paint.any():
            raise SystemExit("预览里可改面积为 0——区域被裁掉了，检查 --pad 与区域位置")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
