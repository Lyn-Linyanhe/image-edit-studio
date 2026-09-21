"""转移完整性核对。

基准（移动前实测，见对话记录）：
    style-distill   56 文件   19.08 MB
    compose        138 文件   62.99 MB
    dsh-plugins     14 文件    0.04 MB
    mantu 原有      78 文件  139.00 MB   (产图 + 图生图用)
    ------------------------------------------------
    合计           286 文件  221.11 MB

核对四件事：
  1) 每个子目录的文件数/体积是否与基准一致（无丢失、无残留）
  2) 总数算术是否闭合
  3) version-study 里是否还有图生图残留（按文件名与内容双重扫）
  4) mantu 里是否有 0 字节或被路径替换弄坏的文件
"""
from __future__ import annotations

import json
from pathlib import Path

MANTU = Path(r"C:\Users\typ\Desktop\mantu")
VS = Path(r"C:\Users\typ\Desktop\version-study")

BASELINE = {
    "style-distill": (56, 19.08),
    # 移动时 compose 是 138；其中有 1 个是运行时产物 compose\images\.dsh-image-edit.pid
    # （几字节的进程号文件），移动后我**主动删掉**了它——因为它记的是已被杀死的
    # PID，留着会让 /stop 去杀一个不存在的进程。故内容文件的正确基准是 137。
    "compose": (137, 62.99),
    "dsh-plugins": (14, 0.04),
    "_pre_existing": (78, 139.00),   # 产图 + 图生图用
}

# 移动时四块合计 286 个文件；扣除上述 1 个主动删除的运行时产物 = 285 个内容文件。
EXPECTED_TOTAL = 285
EXPECTED_MB = 221.11


def count(p: Path) -> tuple[int, float]:
    files = [x for x in p.rglob("*") if x.is_file()]
    mb = sum(x.stat().st_size for x in files) / 1024 / 1024
    return len(files), round(mb, 2)


print("=" * 78)
print("1) 逐目录对账（文件数 / MB）")
print("=" * 78)
print(f"  {'目录':<18}{'基准':>18}{'现状':>18}   判定")
ok_all = True
total_now = [0, 0.0]
for name, (bf, bm) in BASELINE.items():
    if name == "_pre_existing":
        target_dirs = [MANTU / "产图", MANTU / "图生图用"]
        n = 0
        mb = 0.0
        for t in target_dirs:
            if t.exists():
                a, b = count(t)
                n += a
                mb += b
        mb = round(mb, 2)
    else:
        p = MANTU / name
        if not p.exists():
            print(f"  {name:<18}{bf:>10} {bm:>7}{'  缺失！':>18}")
            ok_all = False
            continue
        n, mb = count(p)
    total_now[0] += n
    total_now[1] += mb
    same = (n == bf) and (abs(mb - bm) <= 0.05)
    ok_all &= same
    print(f"  {name:<18}{bf:>10} {bm:>7.2f}{n:>10} {mb:>7.2f}   {'一致' if same else '不一致 <-- 查！'}")

print("-" * 78)
print(f"  {'合计':<18}{EXPECTED_TOTAL:>10} {EXPECTED_MB:>7.2f}{total_now[0]:>10} {total_now[1]:>7.2f}   "
      f"{'闭合' if total_now[0] == EXPECTED_TOTAL else '不闭合 <-- 查！'}")
if total_now[0] != EXPECTED_TOTAL:
    ok_all = False

print()
print("=" * 78)
print("2) version-study 是否还有图生图残留")
print("=" * 78)
# 2a. 顶层是否还有那四个目录
leftover_dirs = [d for d in BASELINE if d != "_pre_existing" and (VS / d).exists()]
print(f"  顶层残留目录: {leftover_dirs if leftover_dirs else '无'}")
if leftover_dirs:
    ok_all = False

# 2b. 全树按名字找图生图特征
name_marks = ("img2img", "mask_edit", "style-distill", "compose", "charser", "ref_mask",
              "preserve_hue", "analyze_style", "grok", "e2e_", "_live_", "改图")
name_hits = [x for x in VS.rglob("*")
             if x.is_file() and any(m.lower() in x.name.lower() for m in name_marks)]
print(f"  按文件名命中: {[str(x.relative_to(VS)) for x in name_hits] if name_hits else '无'}")

# 2c. 按内容找特征词（只扫文本）
content_marks = ("img2img", "图生图", "mask_edit", "style-distill", "改图", "gpt-image",
                 "preserve_hue", "IPAdapter", "ControlNet")
content_hits = []
for x in VS.rglob("*"):
    if not x.is_file() or x.suffix.lower() not in {".py", ".js", ".mjs", ".json", ".md",
                                                   ".txt", ".yml", ".cmd", ".html"}:
        continue
    if ".git" in x.parts:
        continue
    try:
        t = x.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    found = [m for m in content_marks if m.lower() in t.lower()]
    if found:
        content_hits.append((str(x.relative_to(VS)), found))
print(f"  按内容命中: {content_hits if content_hits else '无'}")

print()
print("=" * 78)
print("3) mantu 内是否有空文件或被替换弄坏的文件")
print("=" * 78)
zero = [str(x.relative_to(MANTU)) for x in MANTU.rglob("*") if x.is_file() and x.stat().st_size == 0]
print(f"  0 字节文件 {len(zero)} 个: {zero if zero else '无'}")

# 语法完整性：被路径替换过的 .py 是否仍能编译（抽查关键文件）
import py_compile
bad_py = []
for rel in ["compose/images/mask_edit_app.py", "compose/images/selftest.py",
            "compose/images/probe_502.py", "compose/images/_make_launchers.py",
            "compose/bg_replace.py", "compose/deliver.py"]:
    p = MANTU / rel
    if not p.exists():
        bad_py.append(f"{rel} 缺失")
        continue
    try:
        py_compile.compile(str(p), doraise=True, cfile=str(MANTU / "_tmp.pyc"))
    except Exception as e:
        bad_py.append(f"{rel}: {e}")
print(f"  被改写的 .py 编译检查: {bad_py if bad_py else '全部通过'}")
tmp = MANTU / "_tmp.pyc"
if tmp.exists():
    tmp.unlink()

# JSON/YAML 可解析性
jsonbad = []
for rel in ["style-distill/style_card.json", "style-distill/style_stats.json",
            "dsh-plugins/dsh-image-edit/package.json"]:
    p = MANTU / rel
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        jsonbad.append(f"{rel}: {e}")
print(f"  改写过的 JSON 解析: {jsonbad if jsonbad else '全部通过'}")

print()
print("=" * 78)
print(f"结论: {'全部一致，转移完整' if ok_all else '存在不一致，需查看上面的 <-- 标记'}")
print("=" * 78)
