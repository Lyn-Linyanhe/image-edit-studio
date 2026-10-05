"""量这次两张图在目标尺寸下各自的字节，以及各压缩档的实际效果。

背景：1024×1536 下压缩梯子压到最低档（内容 blur1.6 + scale0.65 + 参考缩小）仍报 2.35 MiB，
不合常理——被模糊并缩到 0.65 倍的图不该还这么大。先出数再决定对策。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "style-distill" / "round_lib", ROOT / "compose" / "images"):
    sys.path.insert(0, str(p))

import run_round as R                                    # noqa: E402

content = Image.open(ROOT / "style-distill/round_arcade/input/C_pose_env_2x3.png").convert("RGB")
ref = Image.open(ROOT / "style-distill/round_arcade/input/B_char_style.png").convert("RGB")

print("  源：内容", content.size, " 参考", ref.size)
print("  内容是否近灰（决定走灰阶档还是模糊档）:", R.is_near_gray(content))

BUDGET = int(1.55 * 1048576)
for tw, th in ((1024, 1536), (1024, 1024), (1536, 1024)):
    c, rs, note = R.pick_reduction(content, [ref], tw, th, "crop", BUDGET)
    cb = R.norm_bytes(c, tw, th, "crop")
    rb = sum(R.norm_bytes(r, tw, th, "crop") for r in rs)
    print(f"\n  === 目标 {tw}×{th} ===")
    print(f"    选择：{note}")
    print(f"    内容 {cb:,} B = {cb/1048576:.2f} MiB   参考 {rb:,} B = {rb/1048576:.2f} MiB"
          f"   合计 {(cb+rb)/1048576:.2f} MiB")

print("\n  === 手工试：把两张源图先降熵，再看合计 ===")
def quant(img: Image.Image, n: int) -> Image.Image:
    return img.convert("P", palette=Image.ADAPTIVE, colors=n).convert("RGB")

for label, c2, r2 in (
    ("原样", content, ref),
    ("参考量化128色", content, quant(ref, 128)),
    ("两图都量化128色", quant(content, 128), quant(ref, 128)),
    ("参考量化96色+缩到600", quant(ref.resize((600, 600), Image.LANCZOS), 96), None),
):
    if r2 is None:
        continue
    cb = R.norm_bytes(c2, 1024, 1536, "crop")
    rb = R.norm_bytes(r2, 1024, 1536, "crop")
    print(f"    {label:22s} 内容 {cb/1048576:.2f} + 参考 {rb/1048576:.2f} = {(cb+rb)/1048576:.2f} MiB")

# 单独看：只发内容、只发参考，各占多少
print("\n  单张占比（1024×1536）：")
print(f"    仅内容 {R.norm_bytes(content, 1024, 1536, 'crop')/1048576:.2f} MiB"
      f"   仅参考 {R.norm_bytes(ref, 1024, 1536, 'crop')/1048576:.2f} MiB")
