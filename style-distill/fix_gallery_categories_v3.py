"""分类规则 v3：按审计结果修两处真错误。

审计（把三类清单逐条打出来看）发现的错误：
  1. `round_lib` 名以 "round_" 开头，被 round-root 规则误判 → round_lib/out_r1..r7.png 7 张
     测试产出被算进"成果"。
  2. "成果"桶混进了非成品：compose/deliver/03_original.png（原图）、04_mask_guide.png（蒙版引导）、
     05_side_by_side.png（对照图）、compose/final{,2}/mask_preview.png（蒙版预览）。

v3：
  · 先判"局部"（更具体的特征优先）：lab 实验件 / redmark / _zoom_ / 蒙版素材(mask_*、mask_preview、
    mask_guide、line_mask)
  · 再判"成果"：round 根层的 out_*（**排除 round_lib**，且不在 work/lab/input 下），
    或 compose 的 out/out2/final/final2/deliver 下且名字不含非成品关键词（original/preview/
    side_by_side/compare/check）
  · 其余 → 过程
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

START = "CATEGORIES = ((\"all\", \"全部\"), (\"deliver\", \"成果\"), (\"detail\", \"局部\"), (\"process\", \"过程\"))"
END = "def _gallery_scan():"

NEW = r'''CATEGORIES = (("all", "全部"), ("deliver", "成果"), ("detail", "局部"), ("process", "过程"))
CAT_LABEL = {"deliver": "成果", "detail": "局部", "process": "过程"}
# 见下方注释：规则经"逐条打印三类清单 + 看图"审计后修订过两处
DETAIL_DIRS = {"lab"}                      # 局部改图实验件（round_*/lab）
DETAIL_HINTS = ("redmark", "_zoom_")        # 涂红预览、局部放大对照
DETAIL_MASKISH = ("mask_", "mask.", "mask_preview", "mask_guide", "line_mask")
DELIVER_DIRS = {"out", "out2", "final", "final2", "deliver"}
# "成果"桶里的非成品：原图/对照/预览/检查 —— 审计时发现它们曾被算成成果
DELIVER_DENY = ("original", "preview", "side_by_side", "compare", "check", "mask")
ROUND_ROOT_DENY = {"round_lib"}            # round_lib 以 "round_" 开头，但不是轮次目录


def gallery_category(rel: str) -> str:
    """按路径特征分到 成果 / 局部 / 过程。

    顺序即优先级：**先判"局部"**（特征更具体），再判"成果"，其余为"过程"。
    规则经 2026-09-22 审计修订：① 排除 round_lib 被误当轮次目录；
    ② 成果桶剔除 original / preview / side_by_side / compare / check / mask 这类非成品。
    """
    import os

    name = os.path.basename(rel).lower()
    segs = [s.lower() for s in rel.replace("\\", "/").split("/")]
    dirs = segs[:-1]

    # ---- 局部：局部改图实验件、涂红预览、局部放大对照、蒙版素材
    if set(dirs) & DETAIL_DIRS:
        return "detail"
    if any(h in name for h in DETAIL_HINTS):
        return "detail"
    if name.startswith(("mask",)) or any(h in name for h in DETAIL_MASKISH):
        return "detail"

    # ---- 成果：轮次根层的 out_*，或旧管线的 out/final/deliver 成品
    if name.startswith("out_"):
        round_dirs = [d for d in dirs if d.startswith("round_")]
        if (any(d not in ROUND_ROOT_DENY for d in round_dirs)
                and not (set(dirs) & {"work", "lab", "input", "checks"})):
            return "deliver"
    if set(dirs) & DELIVER_DIRS and not any(k in name for k in DELIVER_DENY):
        return "deliver"

    return "process"


'''

assert t.count(START) == 1, "起点锚点不是 1 处"
assert t.count(END) == 1, "终点锚点不是 1 处"
i0, i1 = t.index(START), t.index(END)
P.write_text(t[:i0] + NEW + t[i1:], encoding="utf-8")
print(f"  已替换分类段：{i1 - i0} 字 → {len(NEW)} 字")
py_compile.compile(str(P), doraise=True)
print("  编译通过")
