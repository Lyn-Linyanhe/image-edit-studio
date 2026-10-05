#!/usr/bin/env python3
"""风格蒸馏 · 输入体检 与 生成后体检。

audit：投喂前查输入
    python audit_and_check.py audit <path> [<path> ...]
    逐项：路径 / 尺寸 / 短哈希 / 组内重复 / 跨文件同一文件 / 同质性提示

check：生成后查输出
    python audit_and_check.py check --target 原始目标图.png --out 结果图.png [--box x0,y0,x1,y1]
    逐项：尺寸是否一致 / 纸白占比变化 / 指定区域的色相漂移（Lab）

只做事实核验，不做风格判断，也不估算任何数值。
"""
from __future__ import annotations

import argparse
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def short_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def collect(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        q = Path(p)
        if q.is_dir():
            out += sorted(f for f in q.iterdir() if f.suffix.lower() in IMG_EXT)
        elif q.is_file():
            out.append(q)
        else:
            print(f"  ! 找不到: {p}", file=sys.stderr)
    return out


def cmd_audit(args: argparse.Namespace) -> int:
    files = collect(args.paths)
    if not files:
        print("没有可检查的图片。")
        return 1

    info = []
    for f in files:
        try:
            with Image.open(f) as im:
                size = im.size
        except Exception as e:  # noqa: BLE001
            size = ("读取失败", str(e)[:40])
        info.append({"path": f, "size": size, "hash": short_hash(f)})

    print("== 文件台账 ==")
    for r in info:
        print(f"  {r['hash']}  {str(r['size']):>14}  {r['path']}")

    # 跨文件同一文件
    by_hash: dict[str, list[Path]] = {}
    for r in info:
        by_hash.setdefault(r["hash"], []).append(r["path"])
    dups = {h: ps for h, ps in by_hash.items() if len(ps) > 1}
    print("\n== 去重核验 ==")
    if dups:
        for h, ps in dups.items():
            names = " | ".join(str(p) for p in ps)
            print(f"  !! 同一文件出现 {len(ps)} 次  {h}  ->  {names}")
            roles = {p.parent.name for p in ps}
            if len(roles) > 1:
                print("     -> 该文件同时承担了不同目录/角色的输入，等于同一张图被当成来源又当成目标，必须先解决")
    else:
        print("  未发现跨文件重复。")

    # 同质性提示（同一目录、尺寸一致、文件名时间戳相邻）
    print("\n== 同质性提示 ==")
    groups: dict[Path, list[dict]] = {}
    for r in info:
        groups.setdefault(r["path"].parent, []).append(r)
    for d, rs in groups.items():
        if len(rs) < 3:
            continue
        sizes = {r["size"] for r in rs}
        note = [f"  {d}: {len(rs)} 张"]
        if len(sizes) == 1:
            note.append("尺寸全一致")
        stems = [r["path"].stem for r in rs]
        digits = [s for s in stems if s.isdigit()]
        if len(digits) == len(stems):
            n = sorted(int(s) for s in digits)
            span = (n[-1] - n[0]) / 1000.0
            if span <= 600:
                note.append(f"文件名均为数字且跨度 {span:.0f} 秒")
        print("，".join(note))
        if len(sizes) == 1 and len(digits) == len(stems):
            print("     -> 疑似同一批次产出：'共同手法'里可能混着同一生成配置的产物，"
                  "需要补一组'同角色/同内容、换风格'的对照才能证伪")
            print("     -> 若这一组是同一角色，用 R7：投喂张数取最少，并逐条列身份拦截词")

    print("\n== 待你填的角色分配表（同一张图不得同时当身份源与姿态源）==")
    for i, r in enumerate(info, 1):
        print(f"  图{i} | {r['path']} | 角色: ______ | 同时承担了几个角色: ___")
    return 0


def lab_hue_chroma(rgb: np.ndarray) -> tuple[float, float]:
    """返回该区域的平均 Lab 色相角（度）与平均彩度。

    注意 PIL 的 LAB 模式把 a*/b* 存成无符号字节，
    需要按 int8 重新解释（>127 减 256），不能减 128。
    已用纯红校验：raw(81,70) -> a*=+81 b*=+70，与标准值 (+80.09, +67.20) 一致。
    """
    im = Image.fromarray(rgb.astype(np.uint8)).convert("RGB").convert("LAB")
    lab = np.asarray(im).astype(np.int16)
    a = lab[..., 1].astype(np.float32)
    b = lab[..., 2].astype(np.float32)
    a = np.where(a > 127, a - 256, a)
    b = np.where(b > 127, b - 256, b)
    hue = math.degrees(math.atan2(float(b.mean()), float(a.mean())))
    chroma = float(np.hypot(a, b).mean())
    return hue, chroma


def paper_white_ratio(rgb: np.ndarray) -> float:
    m = (rgb[..., 0] > 0.94 * 255) & (rgb[..., 1] > 0.94 * 255) & (rgb[..., 2] > 0.94 * 255)
    return float(m.mean())


def cmd_check(args: argparse.Namespace) -> int:
    t_path, o_path = Path(args.target), Path(args.out)
    A = np.asarray(Image.open(t_path).convert("RGB")).astype(np.float32)
    B = np.asarray(Image.open(o_path).convert("RGB")).astype(np.float32)
    print(f"  目标图 {t_path.name}  {A.shape[1]}x{A.shape[0]}")
    print(f"  结果图 {o_path.name}  {B.shape[1]}x{B.shape[0]}")
    if A.shape != B.shape:
        print("  !! 尺寸不一致：做像素级色相兜底或贴回文字之前，必须先把两者重采样到同一尺寸")

    print(f"\n  纸白占比   目标 {paper_white_ratio(A):.3f}   结果 {paper_white_ratio(B):.3f}")

    if args.box:
        x0, y0, x1, y1 = (int(v) for v in args.box.split(","))
        ha, ca = lab_hue_chroma(A[y0:y1, x0:x1])
        hb, cb = lab_hue_chroma(B[y0:y1, x0:x1])
        d = (hb - ha + 180) % 360 - 180
        print(f"\n  区域 ({x0},{y0})-({x1},{y1}) 色相：目标 {ha:+.1f}°  结果 {hb:+.1f}°  差 {d:+.1f}°")
        print(f"  该区彩度：目标 {ca:.1f}  结果 {cb:.1f}")
        print("  判据参考：色相差在 ±15° 内通常可视为没有跨色相漂移；超过 ±30° 视为漂移，"
              "需要按 COLOUR LOCK 重新约束或走像素级兜底。")
        print("  !! 区域比对只在两张图**几何大致对齐**时才有意义。若本轮改过姿态或构图，"
              "同一坐标框到的已经不是同一样东西，请改为分别对'锁定元素的局部裁切'取样，或直接人工比对。")
    else:
        ha, ca = lab_hue_chroma(A)
        hb, cb = lab_hue_chroma(B)
        print(f"\n  全图平均色相：目标 {ha:+.1f}°  结果 {hb:+.1f}°（全图均值会被内容占比稀释，"
              f"锁色相请用 --box 指定该元素的区域再看）")
        print(f"  全图平均彩度：目标 {ca:.1f}  结果 {cb:.1f}"
              f"   （本轮若要求灰度化，结果应显著接近 0；若要求保留配色，结果不应明显低于目标）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="风格蒸馏：输入体检 / 生成后体检")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("audit", help="投喂前查输入")
    p1.add_argument("paths", nargs="+")

    p2 = sub.add_parser("check", help="生成后查输出")
    p2.add_argument("--target", required=True)
    p2.add_argument("--out", required=True)
    p2.add_argument("--box", default="", help="x0,y0,x1,y1，锁定元素的区域")

    args = ap.parse_args()
    return cmd_audit(args) if args.cmd == "audit" else cmd_check(args)


if __name__ == "__main__":
    raise SystemExit(main())
