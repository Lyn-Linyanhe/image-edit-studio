"""v6 修两处：
  ① round_abs 拼路径漏了 style-distill 这层 → README 的 ✓ 永远读不到，成果全变候选；
  ② 我的草稿区 style-distill/_probe/ 与 round_lib 的临时拼版会被 "check/grid/_sheet"
     命中而落进"对照" → 加 PROCESS_DIRS（先于对照判定）。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    ("ROUND_ROOT_DENY = {\"round_lib\"}            # round_lib 以 \"round_\" 开头，但不是轮次目录",
     "ROUND_ROOT_DENY = {\"round_lib\"}            # round_lib 以 \"round_\" 开头，但不是轮次目录\n"
     "PROCESS_DIRS = {\"_probe\"}                 # 我的草稿区（审阅拼版等）→ 一律过程"),
    ("    # ---- 我自己的测试残留：一律过程（要排在\"对照/局部\"之前）\n"
     "    if name.startswith(SCRATCH_HINTS):\n"
     "        return \"process\"",
     "    # ---- 我自己的测试残留/草稿区：一律过程（要排在\"对照/局部\"之前）\n"
     "    if name.startswith(SCRATCH_HINTS) or (set(dirs) & PROCESS_DIRS):\n"
     "        return \"process\""),
    ("            round_abs = os.path.join(GALLERY_REL_BASE, "
     "*([d for d in dirs if d.startswith(\"round_\")][0:1]))",
     "            # 注意：要拼**完整相对目录**（含 style-distill 那一层），\n"
     "            # 早先只拼了轮次目录名，README 永远读不到 → 成果全被误判成候选。\n"
     "            round_abs = os.path.join(GALLERY_REL_BASE, *dirs)"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:56]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
