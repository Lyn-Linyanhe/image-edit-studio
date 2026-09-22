"""判 L6 有没有救：词库里能抽出什么、提示词里到底抄没抄。

第一版 L6 用正则从（）里抽短语，抽到的是"历史依据"这类注释文字，
所以 33 个文件全报 0。这里试从 ``` 代码块里抽真正的负向短语。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(".").resolve()
SKILL = ROOT / "style-distill" / "_skill" / "style-distill"

lib = (SKILL / "references" / "negative-library.md").read_text(encoding="utf-8")
blocks = re.findall(r"```(.*?)```", lib, re.S)
terms = {t.strip().lower() for b in blocks for t in re.split(r"[,\n]", b) if t.strip()}
print(f"  词库代码块 {len(blocks)} 个 → 可抽取英文短语 {len(terms)} 条")
print(f"    例：{sorted(terms)[:4]}")
print(f"    短于 4 字符的噪声项：{sorted(t for t in terms if len(t) < 4)[:8]}")

ps = sorted(ROOT.glob("style-distill/round_*/prompt_*.txt"))
print(f"\n  提示词 {len(ps)} 个")
hit_files = []
for p in ps:
    t = p.read_text(encoding="utf-8").lower()
    n = sum(1 for x in terms if x in t)
    if n:
        hit_files.append((p.name, n))
print(f"  含英文负向短语的提示词：{len(hit_files)}/{len(ps)}")
for n, c in hit_files[:12]:
    print(f"    {n}: {c} 条")

zh = [p.name for p in ps if "不要" in p.read_text(encoding="utf-8")]
print(f"\n  含中文负向「不要」的提示词：{len(zh)}/{len(ps)}")

# 只报数字与判据，不下结论（工具替人下结论会骗人——2026-09-22 教训）
print("\n  判据（自行判读）：")
print("    · 若英文短语命中≈0/33 → 光修抽取方式救不活 L6（词库英文、提示词中文），")
print("      要「做实」必须给每节补中文关键词；")
print("    · 若命中面明显扩大 → 修抽取方式即可让 L6 有区分力。")
print(f"    本次：英文命中 {len(hit_files)}/33；含中文负向 {len(zh)}/33")
