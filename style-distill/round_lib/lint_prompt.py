"""提示词结构校验器（prompt linter）。

设计原则：**只放"可机械判定"的检查**，每条都能指出具体命中/未命中；不做语义猜测。

可判定的检查（L1–L6）：
  L1 负向段存在（含 DO NOT INCLUDE 或明确的负向段）
  L2 **取景／景别措辞存在** ← 这一条针对已知缺陷：prompt_C2.txt 里这类词一个都没有
  L3 色彩守卫与授权一致：声明黑白 → 负向不得含 monochrome/greyscale，且应有中性灰守卫；
     声明保留颜色 → 负向不得含"不要任何色相"
  L4 身份／锁死段存在
  L5 互斥自查：同一主题在正向与负向里出现相反要求（外框／字幕／背景这几类已知易错项）
  L6 失败态是否抄自词库：与 references/negative-library.md 的短语求交集

用法：python lint_prompt.py <提示词文件...>  或  --all-rounds
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SKILL = Path.home() / ".agents" / "skills" / "style-distill"
NEG_LIB = SKILL / "references" / "negative-library.md"

# ⚠ 不要放"构图"进来：C2 含"两格构图"这类更泛的表述，会把"未指定景别"漏报成通过。
# 构图＝内容排布，取景/景别＝镜头尺度，两者不是一回事。
FRAMING = ["取景", "景别", "半身", "全身", "特写", "大头", "镜头"]
IDENTITY = ["锁死", "保留", "身份"]
MONO_AUTH = ["黑白", "去色", "无彩色", "单色"]
KEEP_COLOR = ["保留颜色", "不剔除颜色", "保留配色"]
# 守卫措辞有变体（prompt_cn 写的是「不要出现任何色相」）——精确短语匹配会误报，
# 故按「组件」匹配：命中 ≥2 个组件才算有中性灰守卫。口径由真实样本校准得出。
NEUTRAL_GUARD = ["不要任何色相", "不要出现任何色相", "不要暖黄", "不要偏褐",
                 "不要偏蓝", "不要彩色", "中性灰"]
EXCLUSIVE_PAIRS = [
    ("外框", ["外框", "框线"]),
    ("字幕", ["字幕", "对白", "文字"]),
    ("背景", ["背景"]),
]


def load_library_phrases() -> set[str]:
    if not NEG_LIB.exists():
        return set()
    txt = NEG_LIB.read_text(encoding="utf-8")
    return {m.strip() for m in re.findall(r"[（(]([^（）()]{6,60})[）)]", txt)}


def lint(p: Path, lib: set[str]) -> list[tuple[str, str, str]]:
    t = p.read_text(encoding="utf-8")
    res: list[tuple[str, str, str]] = []

    # L1 负向段
    has_neg = ("DO NOT INCLUDE" in t) or bool(re.search(r"^【?\s*(DO NOT INCLUDE|负向|不要)", t, re.M))
    res.append(("L1 负向段存在", "PASS" if has_neg else "FAIL",
                "命中 DO NOT INCLUDE" if "DO NOT INCLUDE" in t else "未找到明确的负向段标记"))

    # L2 取景/景别
    fh = [k for k in FRAMING if k in t]
    res.append(("L2 取景/景别措辞", "PASS" if fh else "FAIL",
                f"命中 {fh}" if fh else "【一个都没有】——缺取景约束，模型会自行决定景别与取景"))

    # L3 色彩守卫与授权一致
    mono = [k for k in MONO_AUTH if k in t]
    keep = [k for k in KEEP_COLOR if k in t]
    if mono and not keep:
        bad = [w for w in ("monochrome conversion", "full greyscale") if w in t]
        guard = [k for k in NEUTRAL_GUARD if k in t]
        res.append(("L3 色彩守卫一致性", "PASS" if (not bad and len(guard) >= 2) else "FAIL",
                    f"声明黑白；互斥词残留 {bad}（应空）；中性灰守卫组件 {guard}（需 ≥2 个）"))
    elif keep:
        # 「不要去色」在"声明保留颜色"时**是正确的负向**，不能算冲突（第一版把它当冲突 → 误报 3 个文件）。
        bad = [k for k in ("不要任何色相", "不要彩色") if k in t]
        res.append(("L3 色彩守卫一致性", "PASS" if not bad else "FAIL",
                    f"声明保留颜色；冲突词 {bad}"))
    else:
        res.append(("L3 色彩守卫一致性", "WARN", "既没声明黑白也没声明保留颜色——无法判定一致性"))

    # L4 身份/锁死段
    ih = [k for k in IDENTITY if k in t]
    res.append(("L4 身份/锁死段", "PASS" if ih else "WARN", f"命中 {ih}"))

    # L5 互斥自查：正向要求 vs 负向否决
    neg_block = t.split("DO NOT INCLUDE")[-1] if "DO NOT INCLUDE" in t else t[-len(t)//3:]
    pos_block = t[: len(t) - len(neg_block)]
    conflicts = []
    for label, words in EXCLUSIVE_PAIRS:
        pos_yes = any(f"要{w}" in pos_block or f"画{w}" in pos_block or f"保留{w}" in pos_block for w in words)
        neg_no = any(f"不要{w}" in neg_block or f"不画{w}" in neg_block for w in words)
        if pos_yes and neg_no:
            conflicts.append(label)
    res.append(("L5 正负互斥自查", "PASS" if not conflicts else "FAIL",
                f"发现互斥: {conflicts}" if conflicts else "未发现已知互斥对（外框/字幕/背景）"))

    # L6 失败态是否抄自词库
    if lib:
        neg_text = neg_block
        hit = [ph for ph in lib if ph and ph in neg_text]
        res.append(("L6 失败态抄自词库（启发式·未验证）", "WARN",
                    f"词库交集 {len(hit)} 条。**匹配策略未验证**：第一版从括号抽短语，抽到的是注释文字，"
                    f"对全部 33 个文件都报 0 —— 因此这条只作提示，不能当作 FAIL 依据"))
    else:
        res.append(("L6 失败态抄自词库", "WARN", "词库未找到，跳过"))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all-rounds", action="store_true")
    a = ap.parse_args()

    files = [Path(f) for f in a.files]
    if a.all_rounds:
        files = sorted(Path("style-distill").glob("round_*/prompt_*.txt"))
    if not files:
        raise SystemExit("给提示词文件，或用 --all-rounds")

    lib = load_library_phrases()
    print(f"词库短语 {len(lib)} 条；检查 {len(files)} 个提示词\n")
    bad: list[str] = []
    for p in files:
        if not p.exists():
            print(f"[跳过] {p} 不存在")
            continue
        rows = lint(p, lib)
        flags = [r for r in rows if r[1] != "PASS"]
        mark = "OK  " if not flags else ("FAIL" if any(r[1] == "FAIL" for r in rows) else "WARN")
        print(f"[{mark}] {p.name}")
        for name, st, ev in rows:
            if st != "PASS":
                print(f"        {st} {name}: {ev}")
                if st == "FAIL":
                    bad.append(f"{p.name} :: {name}")
        if not flags:
            print("        六项全过")
    print(f"\n汇总：{len(files)} 个文件，{len(bad)} 条 FAIL")
    for b in bad:
        print("  - " + b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
