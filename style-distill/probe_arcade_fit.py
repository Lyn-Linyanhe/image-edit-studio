"""找出把这一轮压进 1.96 MiB 的可行做法（1024×1536）。

已知：内容 1.54 MiB + 参考 1.26 MiB = 2.80 MiB；梯子最狠档仍 2.35 MiB。
原因：norm_bytes 先 normalise_to_size（LANCZOS 放大到目标尺寸）再存 PNG——
      放大破坏调色板结构 + PNG 无损 → 压不动。
本脚本量两件事：
  A) 喂前把源图本地降熵（降采样/量化）后，梯子「原样」档是多少；
  B) 若把投喂编码换成 JPEG，同样两张图各占多少字节。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "style-distill" / "round_lib", ROOT / "compose" / "images"):
    sys.path.insert(0, str(p))

import run_round as R                                    # noqa: E402
from mask_edit_app import normalise_to_size              # noqa: E402

TW, TH = 1024, 1536
content = Image.open(ROOT / "style-distill/round_arcade/input/C_pose_env_2x3.png").convert("RGB")
ref = Image.open(ROOT / "style-distill/round_arcade/input/B_char_style.png").convert("RGB")


def q(img: Image.Image, n: int) -> Image.Image:
    return img.convert("P", palette=Image.ADAPTIVE, colors=n).convert("RGB")


def scale(img: Image.Image, s: float) -> Image.Image:
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def png_bytes(im: Image.Image) -> int:
    return R.norm_bytes(im, TW, TH, "crop")


def jpg_bytes(im: Image.Image, quality: int = 88) -> int:
    b = io.BytesIO()
    normalise_to_size(im, TW, TH, "crop").save(b, "JPEG", quality=quality, optimize=True)
    return len(b.getvalue())


print("  === A) 喂前本地降熵（仍按 PNG 投喂）→ 目标合计 ≤ 1.90 MiB ===")
rows = []
for cl, c2 in (("原样", content),
               ("缩0.75+量化128", q(scale(content, 0.75), 128)),
               ("缩0.6+量化96", q(scale(content, 0.6), 96))):
    for rl, r2 in (("原样", ref),
                   ("缩到700+量化128", q(ref.resize((700, 700), Image.LANCZOS), 128)),
                   ("缩到560+量化96", q(ref.resize((560, 560), Image.LANCZOS), 96))):
        cb, rb = png_bytes(c2), png_bytes(r2)
        tot = (cb + rb) / 1048576
        rows.append((tot, cl, rl, cb, rb))
for tot, cl, rl, cb, rb in sorted(rows):
    flag = "✓" if tot <= 1.90 else "✗"
    print(f"    {flag} 内容[{cl:14s}] {cb/1048576:5.2f} + 参考[{rl:14s}] {rb/1048576:5.2f} = {tot:5.2f} MiB")

print("\n  === B) 同样两张图改用 JPEG 编码（q88 / q92）→ 体积能降到多少 ===")
for lab, im in (("内容 原样", content), ("参考 原样", ref),
                ("内容 缩0.75+量化128", q(scale(content, 0.75), 128)),
                ("参考 缩到700+量化128", q(ref.resize((700, 700), Image.LANCZOS), 128))):
    print(f"    {lab:22s} PNG {png_bytes(im)/1048576:5.2f} MiB | "
          f"JPEG q88 {jpg_bytes(im)/1048576:5.2f} | JPEG q92 {jpg_bytes(im, 92)/1048576:5.2f}")

print("\n  === C) 纯 JPEG 直投的两种组合 ===")
for cl, c2 in (("原样", content), ("缩0.75+量化128", q(scale(content, 0.75), 128))):
    for rl, r2 in (("原样", ref), ("缩到700+量化128", q(ref.resize((700, 700), Image.LANCZOS), 128))):
        tot = (jpg_bytes(c2) + jpg_bytes(r2)) / 1048576
        print(f"    {'✓' if tot <= 1.90 else '✗'} 内容[{cl:14s}] + 参考[{rl:14s}] = {tot:5.2f} MiB（JPEG q88）")
