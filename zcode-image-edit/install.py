#!/usr/bin/env python3
"""把 image-edit 技能与三个斜杠命令装进 ZCode 的用户作用域，并逐项自检。

为什么需要它：ZCode 对技能与命令有**静默丢弃**规则——frontmatter 缺 `name`/`description`、
`description` 超过 1024 字符、命令名不符合 `^[a-z0-9][a-z0-9_:-]{0,63}$`、
命令既无 `description` 又无正文——这些情况**加载器不报错，只是不出现**，
光看文件在不在是发现不了的。所以本脚本在拷贝之后**逐条按这些规则验一遍**。

安装位置（用户作用域，本机实测存在的口径）：
  技能  ~/.agents/skills/<name>/SKILL.md
  命令  ~/.agents/commands/<name>.md      ← 目录可能还不存在，会创建

用法：
  python install.py            # 安装并自检
  python install.py --check    # 只看状态，不改任何文件
  python install.py --dry-run  # 打印将要做什么，不写
"""
from __future__ import annotations
import sys as _sys

# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
SKILL_SRC = PKG / "_skill" / "image-edit"
CMD_SRC = PKG / "commands"
HOME = Path.home()
SKILL_DST = HOME / ".agents" / "skills" / "image-edit"
CMD_DST = HOME / ".agents" / "commands"

CMD_NAME_RX = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,63}$")
DESC_MAX = 1024


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frontmatter(p: Path) -> dict:
    """扁平解析 `---` 块；只取顶层 `key: value`（缩进行忽略，与 ZCode 一致）。"""
    txt = p.read_text(encoding="utf-8", errors="replace")
    if not txt.startswith("---"):
        return {}
    end = txt.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for line in txt[3:end].splitlines():
        if not line.strip() or line[:1] in (" ", "\t"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def validate() -> list[str]:
    """按 ZCode 的丢弃规则校验源文件；返回问题列表（空=全通过）。"""
    bad = []
    sk = SKILL_SRC / "SKILL.md"
    if not sk.is_file():
        bad.append(f"技能源缺失：{sk}")
        return bad
    fm = frontmatter(sk)
    if not fm:
        bad.append("SKILL.md 没有 frontmatter → ZCode 能加载但 name 取目录名、description 为空 → **永不触发**")
    else:
        if not fm.get("name"):
            bad.append("SKILL.md frontmatter 缺 name → **被丢弃**")
        if not fm.get("description"):
            bad.append("SKILL.md frontmatter 缺 description → **被丢弃**")
        elif len(fm["description"]) > DESC_MAX:
            bad.append(f"SKILL.md description {len(fm['description'])} 字符 > {DESC_MAX} → **被丢弃**")
    cmds = sorted(CMD_SRC.glob("*.md"))
    if not cmds:
        bad.append(f"命令源缺失：{CMD_SRC}/*.md")
    for c in cmds:
        if not CMD_NAME_RX.match(c.stem):
            bad.append(f"命令名不合规会被丢弃：{c.name}（须匹配 ^[a-z0-9][a-z0-9_:-]{{0,63}}$）")
        fm = frontmatter(c)
        body = c.read_text(encoding="utf-8", errors="replace")
        if fm:
            body = body.split("\n---", 1)[1] if "\n---" in body else ""
        if not fm.get("description") and not body.strip():
            bad.append(f"命令既无 description 又无正文 → **被丢弃**：{c.name}")
    return bad


def tree(base: Path) -> dict:
    if not base.is_dir():
        return {}
    return {str(p.relative_to(base)).replace("\\", "/"): sha(p)
            for p in base.rglob("*") if p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser(description="安装 image-edit 技能与命令到 ZCode 用户作用域")
    ap.add_argument("--check", action="store_true", help="只查看状态，不改文件")
    ap.add_argument("--dry-run", action="store_true", help="打印将要做的，不写")
    a = ap.parse_args()

    print("== 源文件校验（按 ZCode 的静默丢弃规则）==")
    problems = validate()
    if problems:
        for p in problems:
            print("  ✗ " + p)
        print("  → 先修掉这些，否则装上去也不会出现。")
        return 1
    fm = frontmatter(SKILL_SRC / "SKILL.md")
    print(f"  ✓ 技能 name={fm.get('name')}  description {len(fm.get('description',''))} 字符（上限 {DESC_MAX}）")
    print(f"  ✓ 命令 {len(list(CMD_SRC.glob('*.md')))} 个，命名与 frontmatter 均合规")

    # 源清单
    src_skill = tree(SKILL_SRC)
    src_cmds = {p.name: sha(p) for p in sorted(CMD_SRC.glob("*.md"))}

    dst_skill = tree(SKILL_DST)
    same_skill = src_skill == dst_skill
    print("\n== 当前安装状态 ==")
    print(f"  技能 {SKILL_DST}")
    print(f"    {'已装且与镜像逐哈希一致 ✓' if same_skill and src_skill else '**未装或不一致**'}  "
          f"（源 {len(src_skill)} 个文件 / 目标 {len(dst_skill)} 个）")
    print(f"  命令 {CMD_DST}")
    for name, h in src_cmds.items():
        d = CMD_DST / name
        state = ("一致 ✓" if d.is_file() and sha(d) == h
                 else ("**内容不同**" if d.is_file() else "**未装**"))
        print(f"    {name:20s} {state}")

    if a.check:
        print("\n（--check：未改动任何文件）")
        return 0

    print("\n== 执行 ==")
    if a.dry_run:
        print(f"  将同步 {SKILL_SRC} → {SKILL_DST}")
        print(f"  将复制 {len(src_cmds)} 个命令 → {CMD_DST}")
        print("（--dry-run：未写任何文件）")
        return 0

    # 技能：镜像为源，整目录同步（先删后建，避免残留影子文件）
    if SKILL_DST.exists():
        shutil.rmtree(SKILL_DST)
    shutil.copytree(SKILL_SRC, SKILL_DST)
    print(f"  已同步技能 → {SKILL_DST}")
    CMD_DST.mkdir(parents=True, exist_ok=True)
    for name in src_cmds:
        shutil.copy2(CMD_SRC / name, CMD_DST / name)
    print(f"  已复制 {len(src_cmds)} 个命令 → {CMD_DST}")

    # 装完复验：必须逐哈希一致
    ok = True
    if tree(SKILL_DST) != src_skill:
        ok = False
        print("  ✗ 技能安装后哈希不一致")
    else:
        print("  ✓ 技能逐哈希一致")
    for name, h in src_cmds.items():
        d = CMD_DST / name
        if not (d.is_file() and sha(d) == h):
            ok = False
            print(f"  ✗ 命令不一致：{name}")
    if ok:
        print("  ✓ 命令全部一致")
    print("\n重启 ZCode 会话后生效（技能与命令在会话启动时发现）。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
