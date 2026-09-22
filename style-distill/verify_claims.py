"""核实我在上一轮结论里用到的每一条"事实"，能查的查，查不了的明确标出。

要核的三件事：
  A) 「我漏写过约束（out_C2 的取景）」—— 证据应在提示词文件里：C3 有取景类措辞、C2 没有
  B) 「--mask / --mask-invert 从未真跑过接口」—— 用 git 历史判断蒙版代码何时引入，
     与 pending_urls.json 的运行时间戳比较
  C) 「第 0 问无强制机制」—— 看它是否只作为散文存在、没有任何工具引用它
另外明确列出**文件无法证实**的项。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(".").resolve()
RM = ROOT / "style-distill" / "round_manga"
RL = ROOT / "style-distill" / "round_lib"
SKILL = Path.home() / ".agents" / "skills" / "style-distill"


def sh(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


print("=" * 74)
print("A) 核实「out_C2 漏写了取景约束」")
print("=" * 74)
KEYS = ["取景", "景别", "半身", "特写", "大头", "镜头"]
for name in ("prompt_C2.txt", "prompt_C3.txt", "prompt_C.txt", "prompt_A.txt", "prompt_B.txt"):
    p = RM / name
    if not p.exists():
        print(f"  {name}: 文件不存在")
        continue
    t = p.read_text(encoding="utf-8")
    hits = {k: t.count(k) for k in KEYS if k in t}
    print(f"  {name:<20} 取景类词命中: {hits if hits else '【全部为 0】'}")

print()
print("=" * 74)
print("B) 核实「--mask / --mask-invert 是否真跑过」")
print("=" * 74)
print("  B1 蒙版代码何时进入 git：")
print("    " + (sh(["git", "log", "-S--mask-invert", "--format=%h %ad %s", "--date=iso"]).strip()
                .replace("\n", "\n    ") or "（git 历史里查不到）"))
print("  B2 pending_urls.json 里的运行时间戳：")
pend = RL / "pending_urls.json"
if pend.exists():
    for r in json.loads(pend.read_text(encoding="utf-8")):
        print(f"    {r['ts']}  {Path(r['out']).name}")
print("  B3 记录里有没有任何一次是用蒙版跑的：台账字段为 "
      f"{sorted(json.loads(pend.read_text(encoding='utf-8'))[0].keys()) if pend.exists() else '-'}")
print("    → 台账不含 mask 字段，因此**不能从台账直接判定**；只能靠 B1 与 B2 的时间先后推断。")
print("  B4 提交时间：")
print("    " + sh(["git", "log", "--format=%h %ad %s", "--date=iso", "-4"]).strip().replace("\n", "\n    "))

print()
print("=" * 74)
print("C) 核实「第 0 问无强制机制」")
print("=" * 74)
needle = "该不该用生成做"
targets = [SKILL / "SKILL.md", SKILL / "references" / "template.md"] + sorted(RL.glob("*.py"))
found = []
for p in targets:
    if p.exists() and needle in p.read_text(encoding="utf-8"):
        found.append(str(p).replace(str(Path.home()), "~"))
print(f"  「{needle}」出现于：{found if found else '（无）'}")
print("  → 若只出现在 skill 的说明文本里、任何脚本都不引用它，则「无强制机制」成立（属结构性事实，非推断）。")

print()
print("=" * 74)
print("D) 无法用文件证实的项（如实标注，不作为结论）")
print("=" * 74)
for item in ("本会话是否调用过 skill() 工具",
             "历史上我读网格坐标错了 3 次",
             "本次会话的失败总次数（引号故障计数）"):
    print(f"  · {item} —— 会话转录不在工作区里，**无法用文件核实**")
