"""给 run_round.py 加 --mask-primary 实验开关（锚点必须命中数 == 1，否则立刻停）。

这是 R5 的第三个杠杆：把涂红图当主图发送、不发干净原图。
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("style-distill/round_lib/run_round.py")
t = P.read_text(encoding="utf-8")

pairs = [
    ("            mask_invert: bool = False) -> int:",
     "            mask_invert: bool = False, mask_primary: bool = False) -> int:"),
    ("                          mask_invert=a.mask_invert)",
     "                          mask_invert=a.mask_invert, mask_primary=a.mask_primary)"),
    ("                                  a.check_target or None, mask_p, a.model, a.dry_run, a.ask,\n"
     "                                  a.mask_invert)",
     "                                  a.check_target or None, mask_p, a.model, a.dry_run, a.ask,\n"
     "                                  a.mask_invert, a.mask_primary)"),
    ('    ap.add_argument("--model", default="", help="覆盖模型',
     '    ap.add_argument("--mask-primary", action="store_true",\n'
     '                    help="**实验**：把涂红的视觉蒙版当主图发送（不发干净原图）。"\n'
     '                         "机制：抽掉「照抄原图恢复」的路径，体积也砍半（少一张全尺寸图）")\n'
     '    ap.add_argument("--model", default="", help="覆盖模型'),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:64]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止，不带着半旧的文件往下走"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
print("  已写入", P)
