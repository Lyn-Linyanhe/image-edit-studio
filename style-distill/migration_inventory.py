"""迁移文档要用到的准确清单：行数、技能镜像与已装副本是否一致、关键文件是否在场。"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(".").resolve()

FILES = [
    "compose/images/mask_edit_app.py",
    "dsh-plugins/dsh-image-edit/lib/client.js",
    "dsh-plugins/dsh-image-edit/lib/index.js",
    "dsh-plugins/dsh-image-edit/package.json",
    "dsh-plugins/dsh-image-edit/cordis.patch.yml",
    "dsh-plugins/dsh-image-edit/README.md",
    "dsh-plugins/_test_client_button.mjs",
    "dsh-plugins/_test_lazy_start.mjs",
    "style-distill/_skill/style-distill/SKILL.md",
    "style-distill/_skill/style-distill/LESSONS.md",
    "style-distill/_skill/style-distill/references/pipeline-notes.md",
    "style-distill/_skill/style-distill/references/template.md",
    "style-distill/_skill/style-distill/references/negative-library.md",
    "style-distill/_skill/style-distill/references/identity-library.md",
    "style-distill/_skill/style-distill/scripts/audit_and_check.py",
    "style-distill/_skill/style-distill/scripts/erase_region.py",
    "style-distill/round_lib/run_round.py",
    "style-distill/round_lib/lint_prompt.py",
    "style-distill/round_lib/local_ops.py",
    "style-distill/round_lib/acceptance.py",
    "style-distill/round_lib/body_report.py",
    "style-distill/round_lib/tone_report.py",
    "style-distill/round_lib/fetch_url.py",
    "style-distill/round_lib/user_inputs.json",
]

print("== 文件行数 ==")
for f in FILES:
    p = ROOT / f
    if p.is_file():
        n = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        print(f"  {n:5d} 行  {p.stat().st_size:>7d} B  {f}")
    else:
        print(f"  {'缺失':>5s}       -  {f}")

print("\n== 技能：镜像 vs 已装副本 ==")
A = ROOT / "style-distill/_skill/style-distill"
B = Path.home() / ".agents" / "skills" / "style-distill"
if not B.is_dir():
    print(f"  已装目录不存在：{B}")
else:
    fa = {p.relative_to(A) for p in A.rglob("*") if p.is_file()}
    fb = {p.relative_to(B) for p in B.rglob("*") if p.is_file()}
    diff = [str(r) for r in fa & fb
            if hashlib.sha256((A / r).read_bytes()).hexdigest()
            != hashlib.sha256((B / r).read_bytes()).hexdigest()]
    print(f"  镜像 {len(fa)} 个文件 / 已装 {len(fb)} 个；哈希不一致：{diff or '无'}")
    print(f"  已装独有：{sorted(map(str, fb - fa)) or '无'}；镜像独有：{sorted(map(str, fa - fb)) or '无'}")

print("\n== SKILL.md 的结构 ==")
skill = (A / "SKILL.md").read_text(encoding="utf-8")
lines = skill.splitlines()
print(f"  总行数 {len(lines)}；二级标题 {sum(1 for ln in lines if ln.startswith('## '))} 个：")
for ln in lines:
    if ln.startswith("## "):
        print(f"    {ln[3:]}")
