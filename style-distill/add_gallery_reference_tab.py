"""分类 v7：加"参考图"页签（第 7 个）。

判据（先扫了真实文件才定）：
  · 参考目录：ref_xiami / references / refs / pose_ref / pose_ref2
  · 名字明示：style_ref / pose_ref / pose_style / identity_ref / face_ref / char_ref …
  · 本项目角色分配约定：各轮 `input/` 里 **A/C＝内容图、B/D＝参考图**
    （见 round_arcade / round_manga 的 README 角色分配表）
  刻意**不**匹配 `*_vs_ref*`、`ref_three_views.png` 之类——那些是"输出 vs 参考"的对照件，
  仍归"对照"；我的草稿区 `_probe/` 仍优先归"过程"。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    ('CATEGORIES = (("all", "全部"), ("deliver", "成果"), ("candidate", "候选"), ("detail", "局部"),\n'
     '              ("compare", "对照"), ("process", "过程"))\n'
     'CAT_LABEL = {"deliver": "成果", "candidate": "候选", "detail": "局部",\n'
     '             "compare": "对照", "process": "过程"}',
     'CATEGORIES = (("all", "全部"), ("deliver", "成果"), ("candidate", "候选"), ("reference", "参考"),\n'
     '              ("detail", "局部"), ("compare", "对照"), ("process", "过程"))\n'
     'CAT_LABEL = {"deliver": "成果", "candidate": "候选", "reference": "参考", "detail": "局部",\n'
     '             "compare": "对照", "process": "过程"}'),
    ('SCRATCH_HINTS = ("_smoke", "_dry", "_budget", "_ok_test", "_ledger")   # 我自己的测试残留 → 过程',
     'SCRATCH_HINTS = ("_smoke", "_dry", "_budget", "_ok_test", "_ledger")   # 我自己的测试残留 → 过程\n'
     '# 参考图：参考目录 / 名字明示 / 本项目 input 的 A-C 内容、B-D 参考约定\n'
     'REFERENCE_DIRS = {"ref_xiami", "references", "refs", "pose_ref", "pose_ref2"}\n'
     'REFERENCE_HINTS = ("style_ref", "pose_ref", "pose_style", "identity_ref", "face_ref",\n'
     '                   "char_ref", "ref_face", "ref_style")\n'
     'REFERENCE_INPUT_PREFIX = ("b_", "d_")    # 角色分配约定：A/C＝内容图，B/D＝参考图\n'
     'CONTENT_INPUT_PREFIX = ("a_", "c_")      # 仅用于说明，不参与判定'),
    ('    # ---- 局部：局部改图实验件、涂红预览、局部放大对照、蒙版素材\n'
     '    if set(dirs) & DETAIL_DIRS:',
     '    # ---- 参考图：参考目录、名字明示、input 里的 B/D 约定\n'
     '    in_input = "input" in dirs\n'
     '    if (set(dirs) & REFERENCE_DIRS\n'
     '            or any(h in name for h in REFERENCE_HINTS)\n'
     '            or (in_input and name.startswith(REFERENCE_INPUT_PREFIX))):\n'
     '        return "reference"\n'
     '\n'
     '    # ---- 局部：局部改图实验件、涂红预览、局部放大对照、蒙版素材\n'
     '    if set(dirs) & DETAIL_DIRS:'),
    ('.c-compare{color:#9adbd3;border-color:#2f4f4c}',
     '.c-compare{color:#9adbd3;border-color:#2f4f4c}'
     '.c-reference{color:#c9b6ff;border-color:#443a63}'),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:54]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
