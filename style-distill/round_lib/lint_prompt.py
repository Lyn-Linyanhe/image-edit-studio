"""提示词结构校验器（prompt linter）。

设计原则：**只放"可机械判定"的检查**，每条都能指出具体命中/未命中；不做语义猜测。

可判定的检查（L1–L6）：
  L1 负向段存在（含 DO NOT INCLUDE 或明确的负向段）
  L2 **取景／景别措辞存在** ← 这一条针对已知缺陷：prompt_C2.txt 里这类词一个都没有
  L3 色彩守卫与授权一致：声明黑白 → 负向不得含 monochrome/greyscale，且应有中性灰守卫；
     声明保留颜色 → 负向不得含"不要任何色相"
  L4 身份／锁死段存在
  L5 互斥自查：同一主题在正向与负向里出现相反要求（外框／字幕／背景这几类已知易错项）

**已删除 L6（2026-09-22）**：原 L6 想检查"失败态是否抄自词库"，但
  ① 第一版从（）里抽短语，抽到的是注释文字，33 个文件全报 0；
  ② 改从 ``` 代码块抽（能抽出 59 条干净英文短语）后实测**只有 3/33 份提示词含英文短语**——
     因为**词库是英文、提示词是中文**，英文匹配在本仓语境下没有判别力。
  所以这条不具备"可机械判定"的资格，改为在汇总处打印一句说明，把"抄词库"交回
  SKILL.md 作业纪律（拼提示词时逐条打开词库）手工执行。不保留会误导人的 0 命中。

豁免（lint_waivers.txt）：已交付轮次的提示词是**当时实际发出的原文**，不能为过校验而改写。
  豁免项在汇总里单独列出并附理由，**不会把 FAIL 变成 PASS**。

用法：python lint_prompt.py <提示词文件...>  或  --all-rounds
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ⚠ 不要放"构图"进来：C2 含"两格构图"这类更泛的表述，会把"未指定景别"漏报成通过。
# 构图＝内容排布，取景/景别＝镜头尺度，两者不是一回事。
FRAMING = ["取景", "景别", "半身", "全身", "特写", "大头", "镜头"]
IDENTITY = ["锁死", "保留", "身份"]
MONO_AUTH = ["黑白", "去色", "无彩色", "单色"]
# 「不要整体去色」「不得去色」这类**否定式**不是授权，不能算"声明黑白"。
# 口径由 prompt_masktest*.txt 暴露（含"不要整体去色"却被判成声明黑白 → 误报 2 个文件）。
NEG_PREFIX = ("不要", "不得", "禁止", "不能", "不可", "无需", "勿", "别")
# 出现这些＝这是"输出要彩色"的任务（例如上色任务），"黑白"只是在描述**输入**
# —— 口径由 prompt_colorize.txt 暴露（它含"上色/配色参考"却含"黑白"）
COLOR_TASK = ["上色", "配色参考"]
KEEP_COLOR = ["保留颜色", "不剔除颜色", "保留配色", "保留原配色",
              "不要改变配色", "不改变配色", "不要改变整体配色", "保持配色", "不要动配色"]
# 冲突词要区分「要灰色」与「要色相稳定」：后者（…任何色相**变化**）在保留颜色的任务里是正确的负向。
HUE_STABILITY_SUFFIX = ("变化", "偏移", "漂移", "迁移", "转换")
# 守卫措辞有变体（prompt_cn 写的是「不要出现任何色相」）——精确短语匹配会误报，
# 故按「组件」匹配：命中 ≥2 个组件才算有中性灰守卫。口径由真实样本校准得出。
NEUTRAL_GUARD = ["不要任何色相", "不要出现任何色相", "不要暖黄", "不要偏褐",
                 "不要偏蓝", "不要彩色", "中性灰"]
EXCLUSIVE_PAIRS = [
    ("外框", ["外框", "框线"]),
    ("字幕", ["字幕", "对白", "文字"]),
    ("背景", ["背景"]),
]


def mono_authorizations(t: str) -> list[str]:
    """MONO_AUTH 里**非否定式**的出现才算"声明黑白"（"不要整体去色"不算）。"""
    hits = []
    for k in MONO_AUTH:
        for m in re.finditer(re.escape(k), t):
            pre = t[max(0, m.start() - 6):m.start()]
            if not any(n in pre for n in NEG_PREFIX):
                hits.append(k)
                break
    return hits


def color_conflicts(t: str) -> list[str]:
    """保留颜色的任务里，"要灰色"的守卫词才算冲突；"不要任何色相**变化**"是色相稳定，不算。"""
    hits = []
    for w in ("不要任何色相", "不要彩色"):
        for m in re.finditer(re.escape(w), t):
            if not t[m.end():m.end() + 2].startswith(HUE_STABILITY_SUFFIX):
                hits.append(w)
                break
    return hits


def lint(p: Path) -> list[tuple[str, str, str]]:
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
    mono = mono_authorizations(t)
    keep = [k for k in KEEP_COLOR if k in t]
    color_task = [k for k in COLOR_TASK if k in t]
    if color_task:
        mono, keep = [], color_task or keep   # 明确是彩色输出的任务 → 归入"保留颜色"分支
    if mono and not keep:
        bad = [w for w in ("monochrome conversion", "full greyscale") if w in t]
        guard = [k for k in NEUTRAL_GUARD if k in t]
        res.append(("L3 色彩守卫一致性", "PASS" if (not bad and len(guard) >= 2) else "FAIL",
                    f"声明黑白；互斥词残留 {bad}（应空）；中性灰守卫组件 {guard}（需 ≥2 个）"))
    elif keep:
        # 「不要去色」在"声明保留颜色"时**是正确的负向**，不能算冲突（第一版把它当冲突 → 误报 3 个文件）。
        # 「不要任何色相**变化**」同理，是色相稳定要求，不是要灰色（第六次校准，由 prompt_masktest*.txt 暴露）。
        bad = color_conflicts(t)
        res.append(("L3 色彩守卫一致性", "PASS" if not bad else "FAIL",
                    f"声明保留颜色 {keep[:2]}；冲突词 {bad}"))
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

    # L6 已删除（见文件头说明）：英文词库对中文提示词无判别力，逐文件报 0 只会变成噪声。
    return res


WAIVERS = Path(__file__).resolve().parent / "lint_waivers.txt"


def load_waivers() -> dict[tuple[str, str], str]:
    """读取豁免清单：{(提示词文件名, 检查项前缀): 理由}。"""
    out: dict[tuple[str, str], str] = {}
    if not WAIVERS.exists():
        return out
    for line in WAIVERS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 3:
            continue
        out[(Path(parts[0]).name, parts[1])] = " ".join(parts[2:])
    return out


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

    waivers = load_waivers()
    print(f"检查 {len(files)} 个提示词；豁免 {len(waivers)} 条\n")
    bad: list[str] = []
    waived: list[str] = []
    for p in files:
        if not p.exists():
            print(f"[跳过] {p} 不存在")
            continue
        rows = lint(p)
        fails = [(name, ev) for name, st, ev in rows if st == "FAIL"]
        wmap: dict[str, str] = {}
        for name, _ev in fails:
            key = next((k for k in waivers if k[0] == p.name and name.startswith(k[1])), None)
            if key:
                wmap[name] = waivers[key]
            else:
                bad.append(f"{p.name} :: {name}")
        flags = [r for r in rows if r[1] != "PASS"]
        mark = ("豁免" if (fails and len(wmap) == len(fails))
                else "FAIL" if fails else "WARN" if flags else "OK  ")
        print(f"[{mark}] {p.name}")
        for name, st, ev in rows:
            if st != "PASS":
                print(f"        {st} {name}: {ev}")
            if st == "FAIL" and name in wmap:
                waived.append(f"{p.name} :: {name} —— {wmap[name]}")
        if not flags:
            print("        五项全过")
    print(f"\n汇总：{len(files)} 个文件，{len(bad)} 条未处置 FAIL，{len(waived)} 条已豁免")
    for b in bad:
        print("  ✗ " + b)
    for w in waived:
        print("  · 已豁免 " + w)
    print("\n注：失败态词库覆盖检查（原 L6）已删除——词库是英文、提示词是中文，"
          "英文短语仅命中 3/33，无判别力。\n    「拼提示词时逐条打开词库抄失败态」按 SKILL.md 作业纪律手工执行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
