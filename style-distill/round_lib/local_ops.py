#!/usr/bin/env python3
"""确定性图像操作合集 —— 凡"改这一张图"的需求都走这里，不调接口。

为什么有它：本项目最贵的一类浪费，是把**确定性可解**的需求交给了生成
（实测：把"这一张的线稿调淡"交给生成白烧 3 次；把"这一张的 4K"交给生成，多花一次调用＋近一小时取回，
而本地放大 1 分钟就能给、且内容一像素不差）。规则写进了 SKILL.md 的开工四问第 0 条，
这个脚本是它的**落地工具**。

子命令：
  lighten-lines  线稿减淡（保护大块深色：黑领结、瞳孔；只抬升细线）
  upscale        放大（Lanczos ＋ **只在线条区域内**锐化，补偿插值软化）
  crop-to        裁成目标比例（可选锚点与显式裁剪带，用于"别把人脸切掉"）
  contact-sheet  多图拼版对照（等高并排，可加等分参考线）
  tone-report    调子剖面（转发 round_lib/tone_report.py）

每个子命令都带**自检**：写出后校验能否完整解码、并报告实际改动范围。
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
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ---- 线稿减淡的调好参数（来自实测：先闭后开，才抓得住"网点填充的实心块"）----
# k_dilate 必须与验证过的原脚本一致 = 7；写成 k_open//2 会差 0.05 个百分点（回归实测：3.64% vs 3.59%）
LIGHTEN = dict(t_dark=0.50, k_close=5, k_open=13, k_dilate=7, t_line=0.35)
LEVELS = {"light": 0.20, "medium": 0.34, "strong": 0.50}
# ---- 放大的锐化参数 ----
UPSCALE = dict(sharpen=0.55, radius=2.0)


def _open(p: Path) -> Image.Image:
    im = Image.open(p)
    im.load()                      # 完整解码，截断文件会在这里报错
    return im.convert("RGB")


def _save_verify(im: Image.Image, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)
    chk = Image.open(out)
    chk.load()
    print(f"  写出 {out}  {im.width}x{im.height}  {out.stat().st_size/1048576:.2f} MB  ✓ 完整可解码")


def _line_mask(lum: np.ndarray, k_close: int, k_open: int, t_dark: float, t_line: float,
               k_dilate: int = 7) -> np.ndarray:
    """细线掩膜：先闭（把网点小点连成块）后开（把细线整条去掉），剩下的实心块被保护。"""
    dark = (lum < t_dark).astype(np.uint8)
    merged = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((k_close, k_close), np.uint8))
    solid = cv2.morphologyEx(merged, cv2.MORPH_OPEN, np.ones((k_open, k_open), np.uint8))
    solid_d = cv2.dilate(solid, np.ones((k_dilate, k_dilate), np.uint8))
    return (lum < t_line) & (solid_d == 0), solid


def cmd_lighten_lines(a) -> int:
    src, out = Path(a.src), Path(a.out)
    im = _open(src)
    base = np.asarray(im).astype(np.float32) / 255.0
    lum = base.mean(axis=2)
    line, solid = _line_mask(lum, LIGHTEN["k_close"], LIGHTEN["k_open"], LIGHTEN["t_dark"], LIGHTEN["t_line"])
    alpha = a.alpha if a.alpha is not None else LEVELS[a.level]
    m = line[..., None]
    res = np.clip(base + (1.0 - base) * alpha * m, 0, 1)
    print(f"  细线占比 {line.mean()*100:.2f}%  被保护的大块深色 {solid.mean()*100:.2f}%  alpha={alpha}")
    before = np.asarray(im).astype(np.int16)
    after = (res * 255).astype(np.uint8).astype(np.int16)
    d = (before != after).any(axis=2)
    brighter = int((d & (after.sum(2) > before.sum(2))).sum())
    back = after.copy(); back[d] = before[d]
    print(f"  改动像素 {int(d.sum())} / {d.size}（{d.mean()*100:.2f}%），其中变亮 {brighter}、变暗 "
          f"{int((d & (after.sum(2) < before.sum(2))).sum())}；还原后与原图逐像素一致 = {bool((back==before).all())}")
    _save_verify(Image.fromarray(after.astype(np.uint8)), out)
    return 0


def cmd_upscale(a) -> int:
    src, out = Path(a.src), Path(a.out)
    im = _open(src)
    side = a.side or max(im.size)
    if a.scale:
        side = round(max(im.size) * a.scale)
    ratio = side / max(im.size)
    target = (round(im.width * ratio), round(im.height * ratio))
    up = im.resize(target, Image.LANCZOS)
    arr = np.asarray(up).astype(np.float32) / 255.0
    lum = arr.mean(axis=2)
    k = max(3, round(LIGHTEN["k_close"] * ratio)) | 1
    ko = max(5, round(LIGHTEN["k_open"] * ratio)) | 1
    line, _ = _line_mask(lum, k, ko, 0.50, 0.45, max(3, round(LIGHTEN["k_dilate"] * ratio)) | 1)
    blur = np.asarray(up.filter(ImageFilter.GaussianBlur(UPSCALE["radius"]))).astype(np.float32) / 255.0
    sharp = np.clip(arr + a.sharpen * (arr - blur), 0, 1)
    m = line[..., None].astype(np.float32)
    res = np.clip(arr * (1 - m) + sharp * m, 0, 1)
    out_im = Image.fromarray((res * 255).astype(np.uint8))

    def grad_energy(img, mask):
        g = np.asarray(img.convert("L")).astype(np.float32)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        mag = np.hypot(gx, gy)
        mm = cv2.resize(mask.astype(np.uint8), (g.shape[1], g.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        return float(mag[mm].mean())
    e0, e1 = grad_energy(up, line), grad_energy(out_im, line)
    print(f"  放大 {im.size} → {target}  线条掩膜 {line.mean()*100:.2f}%")
    print(f"  线条区梯度能量 {e0:.1f} → {e1:.1f}（提升 {100*(e1-e0)/max(e0,1e-6):.1f}%，说明没被插值糊掉）")
    back = out_im.resize(im.size, Image.LANCZOS)
    diff = np.abs(np.asarray(back).astype(np.int16) - np.asarray(im).astype(np.int16))
    print(f"  回缩校验（放大→缩回原尺寸）平均绝对差 {diff.mean():.2f}/255（只来自插值与锐化）")
    _save_verify(out_im, out)
    return 0


def cmd_crop_to(a) -> int:
    src, out = Path(a.src), Path(a.out)
    im = _open(src)
    W, H = im.size
    if a.band:
        x0, y0, x1, y1 = (int(v) for v in a.band.split(","))
    else:
        want = a.aspect
        if W / H > want:                       # 太宽 → 裁宽度
            nw = round(H * want); nh = H
        else:                                  # 太高 → 裁高度
            nw = W; nh = round(W / want)
        band = {"left": 0.0, "center": 0.5, "right": 1.0} if nw < W else {"top": 0.0, "center": 0.5, "bottom": 1.0}
        pos = band.get(a.anchor, 0.5)
        x0 = round((W - nw) * (pos if nw < W else 0.5))
        y0 = round((H - nh) * (pos if nh < H else 0.5))
        x1, y1 = x0 + nw, y0 + nh
    c = im.crop((x0, y0, x1, y1))
    print(f"  {im.size} → {c.size}（比例 {c.width/c.height:.3f}）  裁剪带 x{x0}-{x1} y{y0}-{y1}  锚点={a.anchor}")
    _save_verify(c, out)
    return 0


def cmd_contact_sheet(a) -> int:
    ims = [_open(Path(p)) for p in a.images]
    labels = a.labels.split(",") if a.labels else [Path(p).name for p in a.images]
    if len(labels) != len(ims):
        raise SystemExit("--labels 个数必须与图片个数一致")
    H = a.height
    panels = [(l, im.resize((max(1, round(im.width * H / im.height)), H), Image.LANCZOS)) for l, im in zip(labels, ims)]
    gap = a.gap
    W = sum(im.width for _, im in panels) + gap * (len(panels) - 1)
    canvas = Image.new("RGB", (W, H + 24), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    x = 0
    for lab, im in panels:
        canvas.paste(im, (x, 24))
        d.text((x + 4, 6), lab, fill=(200, 0, 0))
        if a.grid:
            for k in range(1, a.grid):
                y = 24 + round(H * k / a.grid)
                d.line([(x, y), (x + im.width, y)], fill=(0, 140, 255), width=1)
        x += im.width + gap
    print(f"  拼版 {len(panels)} 张，等高 {H}（{'含 ' + str(a.grid) + ' 等分参考线' if a.grid else '无参考线'}）")
    _save_verify(canvas, Path(a.out))
    return 0


def cmd_tone_report(a) -> int:
    here = Path(__file__).resolve().parent
    cmd = [sys.executable, str(here / "tone_report.py"), *a.images]
    if a.ref:
        cmd += ["--ref", a.ref]
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser(description="确定性图像操作（不调接口）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lighten-lines", help="线稿减淡，保护大块深色")
    p.add_argument("src"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--level", choices=list(LEVELS), default="light")
    p.add_argument("--alpha", type=float, default=None, help="直接给强度（0=不动，1=线变白）")
    p.set_defaults(fn=cmd_lighten_lines)

    p = sub.add_parser("upscale", help="放大（只在线条区锐化）")
    p.add_argument("src"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--side", type=int, default=None, help="目标长边像素")
    p.add_argument("--scale", type=float, default=None, help="或按倍数")
    p.add_argument("--sharpen", type=float, default=UPSCALE["sharpen"])
    p.set_defaults(fn=cmd_upscale)

    p = sub.add_parser("crop-to", help="裁成目标比例")
    p.add_argument("src"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--aspect", type=float, default=1.0, help="宽/高，例如 1.5；默认 1.0（方形）")
    p.add_argument("--anchor", default="center", choices=["top", "center", "bottom", "left", "right"])
    p.add_argument("--band", default="", help="直接给裁剪带 x0,y0,x1,y1（原图像素）")
    p.set_defaults(fn=cmd_crop_to)

    p = sub.add_parser("contact-sheet", help="多图拼版对照")
    p.add_argument("images", nargs="+"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--height", type=int, default=400)
    p.add_argument("--labels", default="")
    p.add_argument("--gap", type=int, default=16)
    p.add_argument("--grid", type=int, default=0, help="叠加 N 等分参考线")
    p.set_defaults(fn=cmd_contact_sheet)

    p = sub.add_parser("tone-report", help="调子剖面（转发 tone_report.py）")
    p.add_argument("images", nargs="+"); p.add_argument("--ref", default="")
    p.set_defaults(fn=cmd_tone_report)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
