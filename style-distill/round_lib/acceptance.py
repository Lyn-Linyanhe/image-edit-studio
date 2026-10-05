"""验收：对本次全部优化项做机械检查，输出 PASS/FAIL 表。

原则：每条都用**可复现的命令**验证，不靠叙述。凡需要跑东西的，都真跑。

用法：python style-distill/round_lib/acceptance.py
"""
from __future__ import annotations

import sys as _sys
# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
# ⚠ 必须放在 from __future__ 之后：__future__ 必须是文件的第一条语句（这一条我犯过两次）。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(".").resolve()
RL = ROOT / "style-distill" / "round_lib"
SKILL = Path.home() / ".agents" / "skills" / "style-distill"
BUILD = ROOT / "style-distill" / "_skill" / "style-distill"
RM = ROOT / "style-distill" / "round_manga"
RS = ROOT / "style-distill" / "round_snow"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, evidence: str) -> None:
    RESULTS.append((name, bool(ok), evidence))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}\n         {evidence}")


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)   # ★ 显式 utf-8（本会话的教训）


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    print("=" * 74)
    print("验收 · 逐项机械检查")
    print("=" * 74)

    # ---------- A. skill ----------
    print("\n【A】skill 优化")
    sk = SKILL / "SKILL.md"
    if not sk.exists():
        check("A1 SKILL.md 存在", False, f"找不到 {sk}")
        return 1
    lines = sk.read_text(encoding="utf-8").splitlines()
    heads = [x for x in lines if x.startswith("## ")]
    check("A1 SKILL.md 规模", len(heads) >= 14, f"{len(lines)} 行 / {len(heads)} 个二级标题")

    # 规则可落在主流程（SKILL.md）或模板（template.md）——两者共同构成「skill 内可执行的规则」。
    # （第一版只扫了 SKILL.md，把 4 条按设计放在 template.md 的规则误报成缺失；A3 会单独验 template。）
    text = "\n".join(lines) + "\n" + (SKILL / "references" / "template.md").read_text(encoding="utf-8")
    rules = {
        "确定性优先（开工四问第 0 问）": "这件事该不该用生成做",
        "体积预算节": "体积预算（跑 ≥2K",
        "取回结果作为 5.5 步": "5.5 取回结果",
        "中间稿一律 1K": "中间稿一律 1K",
        "多视图两层清单": "必须**不同**",
        "夸张表情→比例": "表情会连带改比例",
        "验证纪律节": "验证纪律：能出数的就不要靠肉眼",
        "负向双向自查": "双向自查",
        "比例与尺度": "比例与尺度",
        "场景性配件": "场景性配件",
        "改源码必须编译校验": "改源码必须编译校验",
        "作业纪律（命令写脚本）": "作业纪律：命令一律写成脚本文件",
        "局部重绘+反向遮罩": "--mask-invert",
    }
    miss = [k for k, v in rules.items() if v not in text]
    check("A2 13 条规则全部进主流程", not miss, f"命中 {len(rules)-len(miss)}/{len(rules)}" + (f"，缺 {miss}" if miss else ""))

    tmpl = SKILL / "references" / "template.md"
    tm = tmpl.read_text(encoding="utf-8")
    tmiss = [k for k, v in {"比例与尺度": "比例与尺度", "场景性配件": "场景性配件",
                            "负向双向自查": "双向自查", "多视图页附D": "附 D"}.items() if v not in tm]
    check("A3 template.md 四处新增", not tmiss, f"命中 {4-len(tmiss)}/4" + (f"，缺 {tmiss}" if tmiss else ""))

    diff = []
    for p in BUILD.rglob("*"):
        if p.is_file():
            q = SKILL / p.relative_to(BUILD)
            if not q.exists() or sha(p) != sha(q):
                diff.append(str(p.relative_to(BUILD)))
    check("A4 构建副本 == 已装副本", not diff, "逐文件哈希一致" if not diff else f"差异: {diff}")

    # ---------- B. 工具链 ----------
    print("\n【B】工具链")
    for f in ("run_round.py", "local_ops.py", "tone_report.py", "fetch_url.py", "body_report.py"):
        check(f"B1 {f} 存在", (RL / f).exists(), f"{(RL/f).stat().st_size/1024:.0f} KB" if (RL / f).exists() else "缺失")

    helptext = sh([sys.executable, str(RL / "run_round.py"), "--help"]).stdout
    flags = ["--mask", "--mask-invert", "--dry-run", "--ask", "--concurrency", "--model"]
    fmiss = [f for f in flags if f not in helptext]
    check("B2 run_round 六个参数齐全", not fmiss, f"命中 {len(flags)-len(fmiss)}/{len(flags)}" + (f"，缺 {fmiss}" if fmiss else ""))

    rr = (RL / "run_round.py").read_text(encoding="utf-8")
    for label, needle in (("探测式抢档（speed-limit）", "--speed-limit"),
                          ("门槛按实测区间", "20000, 8"),
                          ("URL 落盘台账", "note_pending"),
                          ("完整解码校验", "Image.open(out).load()"),
                          ("局部改图正/反向", "invert=invert")):
        check(f"B3 {label}", needle in rr, "命中" if needle in rr else f"未见 {needle!r}")

    pend = RL / "pending_urls.json"
    ok_pend = False
    ev = "缺失"
    if pend.exists():
        try:
            data = json.loads(pend.read_text(encoding="utf-8"))
            ok_pend = isinstance(data, list) and all("url" in d and "status" in d for d in data)
            ev = f"{len(data)} 条记录，全部含 url/status"
        except Exception as e:  # noqa: BLE001
            ev = f"解析失败 {e}"
    check("B4 pending_urls.json 台账", ok_pend, ev)

    lo_help = sh([sys.executable, str(RL / "local_ops.py"), "--help"]).stdout
    subs = ["lighten-lines", "upscale", "crop-to", "contact-sheet", "tone-report"]
    smiss = [s for s in subs if s not in lo_help]
    check("B5 local_ops 五个子命令", not smiss, f"命中 {len(subs)-len(smiss)}/{len(subs)}" + (f"，缺 {smiss}" if smiss else ""))

    # 回归：lighten-lines 是否与已认可的 s1 逐像素一致
    s1 = RM / "out_v12B_lineLighter_s1.png"
    base = RM / "out_v12B.png"
    if s1.exists() and base.exists():
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "regen.png"
            env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
            sh([sys.executable, str(RL / "local_ops.py"), "lighten-lines", str(base),
                "-o", str(out), "--level", "light"], env=env)
            if out.exists():
                a = np.asarray(Image.open(s1).convert("RGB")).astype(np.int16)
                b = np.asarray(Image.open(out).convert("RGB")).astype(np.int16)
                nd = int((a != b).any(axis=2).sum())
                check("B6 回归：lighten-lines == 已认可的 s1", nd == 0,
                      f"差异像素 {nd}（{'完全一致' if nd == 0 else '不一致'}）；同时验证了「无 PYTHONIOENCODING 也能跑」")
            else:
                check("B6 回归：lighten-lines", False, "重生成失败（可能因缺少 UTF-8 前置而崩）")
    else:
        check("B6 回归：lighten-lines", False, "缺少 s1 或基准图")

    # 所有脚本编译 + UTF-8 前置
    compile_bad, no_pre = [], []
    for p in sorted(RL.glob("*.py")):
        src = p.read_text(encoding="utf-8")
        try:
            compile(src, str(p), "exec")
        except SyntaxError as e:
            compile_bad.append(f"{p.name}: {e}")
        if "reconfigure(encoding=" not in src and p.name != "acceptance.py":
            no_pre.append(p.name)
    check("B7 全部脚本编译通过", not compile_bad, "全部通过" if not compile_bad else f"{compile_bad}")
    check("B8 脚本自带 UTF-8 前置", not no_pre, "全部自带" if not no_pre else f"缺前置: {no_pre}")

    # ---------- C. 流程与工程 ----------
    print("\n【C】流程与工程")
    comfy = []
    scanned = 0
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(ROOT))
        top = rel.split(os.sep)[0]
        # ⚠ 原来用子串 ".git" 判断 → **任何路径含 ".git" 的文件永不被扫描**
        # （活例：`.gitignore` 自己含 comfy 却从来不报）。改为只跳 `.git` 目录本身。
        if top == ".git" or any(x in rel for x in ("node_modules", "npm-cache", "_backup")):
            continue
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue      # 字节码缓存里带着本脚本自己的源码（含检索词）→ 是构建产物，不算残留
        if p.name in ("acceptance.py", ".gitignore"):
            continue      # 检查脚本与忽略规则文件里必须写出检索词本身，不算残留
        if "comfy" in rel.lower():
            comfy.append(f"{rel}（路径名）")
            continue
        if p.suffix.lower() == ".md":
            continue      # **文档里提到这个词不算残留**（本检查与验收报告都会提到它）——
                          # 残留指代码/配置/资产，不指"有人在文档里写下了这个词"
        if p.stat().st_size > 3 * 1024 * 1024:
            continue
        scanned += 1
        try:
            if "comfy" in p.read_text(encoding="utf-8", errors="ignore").lower():
                comfy.append(rel)
        except Exception:
            pass
    check("C1 无 ComfyUI 残留", not comfy,
          f"扫过 {scanned} 个文件（.md 只查路径名），0 处" if not comfy else f"命中: {comfy}")

    deliver = []
    for rd in (RM / "README.md", RS / "README.md"):
        import re
        for line in rd.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^- `([^`]+)` — .*?`(.)\s+([\d.]+ MB)`", line)
            if m:
                f = rd.parent / m.group(1)
                deliver.append((m.group(1), f.exists() and m.group(2) == "✓", m.group(3)))
    okn = sum(1 for _, ok, _ in deliver if ok)
    check("C2 交付件全部在场", okn == len(deliver) and len(deliver) >= 12,
          f"{okn}/{len(deliver)} 在场")

    # R10：顶层 PNG 只能是交付件——原来只管 round_manga，round_snow 顶层曾混放 7 个实验件
    extra_all = {}
    for rd in (RM, RS):
        dn = {n for n, _, _ in deliver if (rd / n).exists()}
        e = [p.name for p in sorted(rd.glob("*.png")) if p.name not in dn]
        if e:
            extra_all[rd.name] = e
    detail = ("、".join(f"{k}: {v}" for k, v in extra_all.items()) if extra_all
              else f"{RM.name}、{RS.name} 顶层均只有交付件")
    check("C3 顶层 PNG 只有交付件（两个 round）", not extra_all, detail)

    gi = sh(["git", "check-ignore", "-v", "style-distill/round_lib/run_round.py"]).stdout.strip()
    check("C4 .gitignore 未误伤工具链", gi == "", "未被忽略 ✓" if not gi else f"被忽略 ← {gi}")

    st = sh(["git", "status", "--porcelain"]).stdout.strip()
    check("C5 git 工作区干净", st == "", "干净 ✓" if not st else f"{len(st.splitlines())} 项未提交")

    logs = sh(["git", "log", "--oneline"]).stdout.strip().splitlines()
    check("C6 有提交记录", len(logs) >= 3, f"{len(logs)} 个提交，最新：{logs[0] if logs else '-'}")

    # dry-run 不发送
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "should_not_exist.png"
        r = sh([sys.executable, str(RL / "run_round.py"), "--content",
                str(RM / "work" / "feed_char_169.png"), "--prompt",
                str(RM / "prompt_threeview_v15.txt"), "--out", str(out),
                "--size", "1024x1024", "--dry-run"])
        check("C7 --dry-run 不发送、不产出文件", ("预算报表" in r.stdout) and (not out.exists()),
              "打印了报表且未产出文件 ✓" if ("预算报表" in r.stdout and not out.exists()) else "异常")

    # 蒙版路径：体积硬门禁（D1）与涂红图落盘（D2）——2026-09-22 验收新增
    # 蒙版要发两张全尺寸图且不走压缩梯子，实测 1536×1024 = 2.15 MiB → HTTP 400。
    # 这里用随机噪声内容做确定性的超限样本（噪声 PNG 必然远超 1.96 MiB）。
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        rnd = np.random.default_rng(0).integers(0, 256, (711, 1067, 3), dtype=np.uint8)
        cpath = tdp / "content.png"
        Image.fromarray(rnd).save(cpath)
        mk = Image.new("L", (1067, 711), 0)
        ImageDraw.Draw(mk).ellipse((370, 200, 490, 296), fill=255)
        mpath = tdp / "mask.png"
        mk.save(mpath)
        out = tdp / "should_not_send.png"
        r = sh([sys.executable, str(RL / "run_round.py"), "--content", str(cpath),
                "--prompt", str(RM / "prompt_threeview_v15.txt"), "--out", str(out),
                "--size", "1536x1024", "--mask", str(mpath)])
        refused = "已拒绝发送" in r.stdout
        never_sent = "HTTP" not in r.stdout and not out.exists()
        dumped = list(tdp.glob("*.redmark.png"))
        check("C8 蒙版超限被拒发（未发送）", refused and never_sent and r.returncode != 0,
              f"returncode={r.returncode}；拒绝提示={refused}；未发出请求={never_sent}")
        check("C9 蒙版涂红图发送前落盘", bool(dumped),
              f"落盘 {[p.name for p in dumped]}" if dumped else "未落盘（发送前无法确认涂红位置）")

    # R1 调用台账：C8 那次被拒发应当已追加一条可回溯记录
    ledger = RL / "call_ledger.jsonl"
    need = {"ts", "out", "size", "pad", "quality", "prompt", "prompt_sha1", "content", "bytes", "result"}
    rec = None
    if ledger.exists():
        lines = [x for x in ledger.read_text(encoding="utf-8").strip().splitlines() if x.strip()]
        if lines:
            rec = json.loads(lines[-1])
    have = set(rec or {})
    check("C10 调用台账可回溯（每次调用留参数）", rec is not None and need <= have,
          f"台账 {len(lines) if ledger.exists() else 0} 条；末条缺字段 {sorted(need - have)}"
          if rec else "台账不存在或无记录")

    # R2 比例守卫：几何不符必须出声，相符时不许误报
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        sq = tdp / "square.png"
        Image.new("RGB", (1024, 1024), (128, 128, 128)).save(sq)
        r_bad = sh([sys.executable, str(RL / "run_round.py"), "--content",
                    str(RM / "work" / "feed_char_169.png"), "--prompt",
                    str(RM / "prompt_threeview_v15.txt"), "--out", str(tdp / "a.png"),
                    "--size", "1024x1024", "--dry-run"])
        r_ok = sh([sys.executable, str(RL / "run_round.py"), "--content", str(sq),
                   "--prompt", str(RM / "prompt_threeview_v15.txt"), "--out", str(tdp / "b.png"),
                   "--size", "1024x1024", "--dry-run"])
        check("C11 比例守卫：不符时警告、相符时不误报",
              ("比例不符" in r_bad.stdout) and ("比例不符" not in r_ok.stdout),
              f"1.78:1 源→1024² {'有' if '比例不符' in r_bad.stdout else '无'}警告；"
              f"1:1 源→1024² {'有' if '比例不符' in r_ok.stdout else '无'}警告")

    # ---------- 汇总 ----------
    n = len(RESULTS)
    ok = sum(1 for _, o, _ in RESULTS if o)
    print("\n" + "=" * 74)
    print(f"验收汇总：{ok}/{n} 项通过" + ("　—— 全部通过 ✓" if ok == n else f"　—— {n-ok} 项未通过"))
    if ok != n:
        print("未通过项：")
        for name, o, ev in RESULTS:
            if not o:
                print(f"  - {name}: {ev}")
    print("=" * 74)
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
