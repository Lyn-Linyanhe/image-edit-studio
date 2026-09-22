"""分类 v5：加"候选"与"对照"两个页签，并让"成果"由 README 的 ✓ 决定。

可判据（不是我拍脑袋）：
  · 各轮 README 的交付件写成 `- `out_XXX.png` — …  `✓  2.73 MB``；
    round_manga 10 条 ✓、round_snow 2 条 ✓、round_arcade 的 out_* 只在候选表里出现、**无 ✓**。
  · 所以：轮次根层 out_* 且在 README 里带 ✓ → 成果；不带 ✓ → **候选**。
  · 对照 = checks/ 与 diag/ 目录，或名字含 compare / side_by_side / _vs_ / _cmp / check /
    grid / _sheet / contact / _ab_ 的对照拼版；但我自己的测试残留（_smoke/_dry/_budget）除外 → 过程。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

BLOCK_START = "CATEGORIES = ((\"all\", \"全部\"), (\"deliver\", \"成果\"), (\"detail\", \"局部\"), (\"process\", \"过程\"))"
BLOCK_END = "def _gallery_scan():"

NEW = r'''CATEGORIES = (("all", "全部"), ("deliver", "成果"), ("candidate", "候选"), ("detail", "局部"),
              ("compare", "对照"), ("process", "过程"))
CAT_LABEL = {"deliver": "成果", "candidate": "候选", "detail": "局部",
             "compare": "对照", "process": "过程"}
# 规则经 2026-09-22 两次审计修订（看图 + 逐条清单 + 断言），详见 fix_gallery_categories*.py
DETAIL_DIRS = {"lab"}                      # 局部改图实验件（round_*/lab）
DETAIL_HINTS = ("redmark", "_zoom")         # 涂红预览、局部放大对照
DETAIL_SUFFIX = ("zoom",)                  # …_zoom.png（名字末尾的 zoom）
DETAIL_MASKISH = ("mask_preview", "mask_guide", "line_mask")
# 对照：输出 vs 参考的对照条、诊断拼版
COMPARE_DIRS = {"checks", "diag"}
COMPARE_HINTS = ("compare", "side_by_side", "_vs_", "_cmp", "check", "grid",
                 "_sheet", "contact", "_ab_")
SCRATCH_HINTS = ("_smoke", "_dry", "_budget", "_ok_test", "_ledger")   # 我自己的测试残留 → 过程
DELIVER_DIRS = {"out", "out2", "final", "final2", "deliver"}
# 旧管线 compose/ 没有交付清单，只能按"成品名"判：以下名字是图层/原图/对照/检查，不算成果
DELIVER_DENY = ("original", "background_only", "bg_only", "bg", "mask", "preview",
                "side_by_side", "compare", "check", "tech")
ROUND_ROOT_DENY = {"round_lib"}            # round_lib 以 "round_" 开头，但不是轮次目录

_ACCEPTED_CACHE: dict[str, set] = {}


def _accepted_names(round_abs: str) -> set:
    """读该轮 README 里带 ✓ 的交付件名（README 是"已认可"的权威来源）。"""
    import os
    import re

    if round_abs in _ACCEPTED_CACHE:
        return _ACCEPTED_CACHE[round_abs]
    found: set = set()
    p = os.path.join(round_abs, "README.md")
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                if "✓" not in line:
                    continue
                found.update(re.findall(r"[A-Za-z0-9_\-]+\.(?:png|jpg|jpeg|webp|gif)", line))
    except OSError:
        found = set()
    _ACCEPTED_CACHE[round_abs] = found
    return found


def gallery_category(rel: str) -> str:
    """按路径特征分到 成果 / 候选 / 局部 / 对照 / 过程。

    优先级：局部（特征最具体） → 对照 → 成果/候选（看 README 有无 ✓） → 过程。
    测试残留（_smoke/_dry/…）先落"过程"，免得混进"对照"或"局部"。
    """
    import os

    name = os.path.basename(rel).lower()
    segs = [s.lower() for s in rel.replace("\\", "/").split("/")]
    dirs = segs[:-1]
    stem = name.rsplit(".", 1)[0]

    # ---- 我自己的测试残留：一律过程（要排在"对照/局部"之前）
    if name.startswith(SCRATCH_HINTS):
        return "process"

    # ---- 局部：局部改图实验件、涂红预览、局部放大对照、蒙版素材
    if set(dirs) & DETAIL_DIRS:
        return "detail"
    if (any(h in name for h in DETAIL_HINTS) or stem.endswith(DETAIL_SUFFIX)
            or name.startswith(("mask",)) or any(h in name for h in DETAIL_MASKISH)):
        return "detail"

    # ---- 对照：对照条与诊断拼版
    if set(dirs) & COMPARE_DIRS or any(h in name for h in COMPARE_HINTS):
        return "compare"

    # ---- 成果 / 候选：轮次根层的 out_*，按该轮 README 有无 ✓ 区分
    if name.startswith("out_"):
        round_dirs = [d for d in dirs if d.startswith("round_") and d not in ROUND_ROOT_DENY]
        if round_dirs and not (set(dirs) & {"work", "lab", "input", "checks"}):
            round_abs = os.path.join(GALLERY_REL_BASE, *([d for d in dirs if d.startswith("round_")][0:1]))
            return "deliver" if name in _accepted_names(round_abs) else "candidate"
    if set(dirs) & DELIVER_DIRS and not any(k in name for k in DELIVER_DENY):
        return "deliver"

    return "process"


'''

assert t.count(BLOCK_START) == 1, "分类段起点锚点不是 1 处"
assert t.count(BLOCK_END) == 1, "分类段终点锚点不是 1 处"
i0, i1 = t.index(BLOCK_START), t.index(BLOCK_END)
t = t[:i0] + NEW + t[i1:]

# 两个新分类的卡片配色
old_css = ".c-process{color:#9fb4cc;border-color:#33445d}"
new_css = (".c-process{color:#9fb4cc;border-color:#33445d}"
           ".c-candidate{color:#ffb4e6;border-color:#5d3350}"
           ".c-compare{color:#9adbd3;border-color:#2f4f4c}")
n = t.count(old_css)
print(f"  CSS 锚点命中 {n} 次")
assert n == 1, "CSS 锚点不是 1 处"
t = t.replace(old_css, new_css)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
