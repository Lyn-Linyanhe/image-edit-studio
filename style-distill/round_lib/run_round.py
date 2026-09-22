#!/usr/bin/env python3
"""一轮作业的全流程一键跑：压缩 → 发送 → 重试 → curl 下载 → 体检。

替代此前每轮手写的七八步：
  1) 按接口表单上限自动压低投喂体积（按"归一化到目标尺寸后"的真实字节判断，
     因为 normalise_to_size 会把每张统一缩放到目标尺寸，按源分辨率压缩是无效的）；
  2) 发送并对上传阶段的瞬时断连（SSL UNEXPECTED_EOF）自动重试；
  3) 先打印结果 URL 再用 curl 下载（该 CDN 上 Python urllib 会挂死）；
  4) 可选跑生成后体检。

用法：
  python run_round.py --content C.png --ref A.png [--ref B.png] \\
      --prompt p.txt --out o.png [--size 1024x1024] [--quality low] \\
      [--budget-mib 1.55] [--check-target T.png] [-n 1]

多方案并行（同一改动、多套提示词）：
  python run_round.py --content C.png --ref A.png \\
      --prompt pA.txt --out oA.png \\
      --prompt pB.txt --out oB.png --concurrency 2
"""
from __future__ import annotations
import sys as _sys
# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
# 这样不依赖 PYTHONIOENCODING 环境变量，也不会影响其它程序（见 SKILL.md 的「作业纪律」）。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


import argparse
import base64
import datetime
import hashlib
import io
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent / "compose" / "images"))
import gen as G  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

CHECK = Path.home() / ".agents" / "skills" / "style-distill" / "scripts" / "audit_and_check.py"


# ---------- 体积压缩 ----------

def norm_bytes(im: Image.Image, tw: int, th: int, pad: str) -> int:
    from mask_edit_app import normalise_to_size  # noqa: WPS433
    b = io.BytesIO()
    normalise_to_size(im.convert("RGB"), tw, th, pad).save(b, "PNG", optimize=True)
    return len(b.getvalue())


def shrink_ref(im: Image.Image, side: int = 448, blur: float = 1.2, ncol: int = 128) -> Image.Image:
    s = side / max(im.size)
    out = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    return out.filter(ImageFilter.GaussianBlur(blur)).quantize(colors=ncol).convert("RGB")


def shrink_content(im: Image.Image, mode: str) -> Image.Image:
    if mode.startswith("gray"):
        n = int(mode[4:])
        return im.convert("L").quantize(colors=n).convert("RGB")
    if mode.startswith("blur"):
        b = float(mode[4:])
        return im.filter(ImageFilter.GaussianBlur(b)).quantize(colors=128).convert("RGB")
    if mode.startswith("scale"):
        s = float(mode[5:])
        return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    return im


def is_near_gray(im: Image.Image, thresh: float = 6.0) -> bool:
    import numpy as np
    a = np.asarray(im.convert("RGB").resize((160, 160))).astype(float)
    sat = np.abs(a - a.mean(axis=2, keepdims=True)).mean()
    return sat < thresh


def pick_reduction(content: Image.Image, refs: list[Image.Image],
                   tw: int, th: int, pad: str, budget: int) -> tuple[Image.Image, list[Image.Image], str]:
    def total(c, rs):
        return norm_bytes(c, tw, th, pad) + sum(norm_bytes(r, tw, th, pad) for r in rs)

    cands: list[tuple[str, Image.Image, list[Image.Image]]] = [("原样", content, refs)]
    refs_small = [shrink_ref(r) for r in refs]
    cands.append(("参考图缩小", content, refs_small))
    if is_near_gray(content):
        for n in (16, 12, 10, 8, 6):
            cands.append((f"内容灰阶{n}级", shrink_content(content, f"gray{n}"), refs_small))
    else:
        for b in (1.0, 1.6):
            cands.append((f"内容模糊{b}", shrink_content(content, f"blur{b}"), refs_small))
    for s in (0.8, 0.65):
        base = shrink_content(content, "gray10") if is_near_gray(content) else shrink_content(content, "blur1.6")
        cands.append((f"内容再缩{s}", shrink_content(base, f"scale{s}"), refs_small))

    for name, c, rs in cands:
        t = total(c, rs)
        if t <= budget:
            return c, rs, f"{name}（合计 {t} B = {t/1048576:.2f} MiB）"
    name, c, rs = cands[-1]
    t = total(c, rs)
    return c, rs, f"！压到最小档仍超预算：{name}（{t} B = {t/1048576:.2f} MiB）"


# ---------- 发送与下载 ----------

def post_with_retry(fields: dict, files: dict, attempts: int = 3, timeout: int = 900):
    """发送，并对**传输层**瞬时失败自动重试。

    ⚠ 2026-09-22 实测修正：原来的 try/except 是**死代码**——`gen.call` 自己不抛异常，
    而是把任何异常吞成 `(-1, "类型: 消息")` 返回，所以模块头承诺的
    "上传阶段 SSL UNEXPECTED_EOF 自动重试"**从未真正生效**（实测撞上
    `UNEXPECTED_EOF_WHILE_READING` 时直接 FAILED、没有一句重试日志）。
    现改为**按返回值**判定：-1（传输层失败）与 5xx 可重试；4xx 是载荷/参数问题，
    重试没有意义，直接返回交给调用方。
    """
    last = None
    for i in range(1, attempts + 1):
        try:
            st, txt = G.call(fields, files, timeout=timeout)
        except Exception as e:  # noqa: BLE001  （gen.call 不抛，但别赌它以后不抛）
            st, txt = -1, f"{type(e).__name__}: {e}"
        if st != -1 and st < 500:
            return st, txt
        last = f"HTTP {st}: {str(txt)[:200]}"
        print(f"   发送第 {i}/{attempts} 次失败（传输层）：{last}", flush=True)
        if i < attempts:
            time.sleep(min(3 * i, 15))
    return -1, f"重试 {attempts} 次仍失败：{last}"


def download(url: str, out: Path, attempts: int = 8, timeout: int = 600) -> None:
    """下载结果图 —— **探测式抢高速档**（本次带宽诊断后的新策略）。

    诊断结论（都是实测）：
      · 本机链路不慢：到 Cloudflare 5,177 KB/s（41 Mbps）；
      · 中转站图片 CDN 送图**极不稳定**：同一主机两次请求 1.26 KB/s ↔ 97.2 KB/s，**差 77 倍**；
      · 该 CDN **不支持 Range**（带 Range 返回 200 而非 206），不能续传、不能分块并行；
      · 图生图不支持内联 base64（`mask_edit_app.py:61/96` 已实测记录），所以绕不开这条 CDN。

    推论：既然速率抖 77 倍，**用一个长超时去傻等是最差策略**——应该"低速就立刻断、重试抢档"。
    curl 自带合用的参数：`--speed-limit <B/s> --speed-time <秒>`（速率持续低于阈值超时就主动中断）。

    ⚠️ 门槛不能定高（首版踩到）：第一版用 (40K,5)(40K,5)(25K,6)(25K,6)…
    **把一次平均 61.6 KB/s 的尝试也杀了**——它中途瞬时掉到 40 KB/s 以下就被 curl 断开。
    实测这台 CDN 的工作区间就是 **20–60 KB/s**，偶尔崩到 1.5 KB/s，所以门槛要按这个区间定：
      · 低于 ~12 KB/s 持续 10 秒 = 没救，断掉重试（这种尝试 900 秒也拿不到 10 MB）；
      · 12–60 KB/s 是正常区间，**必须让它跑完**（10 MB / 20 KB/s ≈ 500 秒，所以要给足 max-time）。
    另外**不支持 Range 意味着没有续传**，每次中断都从头再来，所以门槛越严、浪费的字节越多。

    实测（10 MB / 3840×2160 那个 4K）：
      旧策略：两次 900 秒各只取回约 1.9 MB，均失败 → 30 分钟白费；
      新策略：4 次快速淘汰（110 秒）＋ 第 5 次 12 KB/s 门槛下 511 秒完成 → **约 11 分钟下完**。
    """
    plan = [(20000, 8), (20000, 8), (12000, 10), (12000, 10), (8000, 12), (0, 0), (0, 0), (0, 0)]
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise SystemExit(f"   找不到 curl；URL 已打印，可手工取回：{url}")

    for i, (slimit, stime) in enumerate(plan[:attempts], 1):
        args = [curl, "-sS", "-L", "--max-time", str(timeout)]
        if slimit:
            args += ["--speed-limit", str(slimit), "--speed-time", str(stime)]
        else:
            args += ["--max-time", "1800"]
        args += ["--retry", "1", "--retry-delay", "2", "-A", "curl/8.0", "-o", str(out), url]

        t0 = time.time()
        r = subprocess.run(args, capture_output=True, text=True)
        dt = max(time.time() - t0, 0.1)
        got = out.stat().st_size if out.exists() else 0
        kbps = got / 1024 / dt

        ok = False
        if r.returncode == 0 and got > 1024:
            try:
                Image.open(out).load()          # 完整解码校验：截断文件 open 不报错、load 才报
                ok = True
            except Exception as e:  # noqa: BLE001
                print(f"   第{i}次：文件不完整（{got:,} B）: {e}", flush=True)

        gate = "无门槛" if not slimit else f"{slimit//1000} KB/s×{stime}s"
        if ok:
            print(f"   第{i}次成功：{got:,} B / {dt:.0f} 秒 = {kbps:.1f} KB/s（门槛 {gate}）", flush=True)
            return
        print(f"   第{i}次未通过：{got:,} B / {dt:.0f} 秒 = {kbps:.1f} KB/s"
              f"（门槛 {gate}，rc={r.returncode}）{' ' + r.stderr.strip()[:70] if r.stderr else ''}",
              flush=True)
        time.sleep(min(2 + i, 8))

    raise SystemExit(f"   下载失败（{attempts} 次尝试）；URL 已记入 pending_urls.json，可用 "
                     f"fetch_url.py 补下：{url}")


PENDING = _HERE / "pending_urls.json"


def note_pending(out_p: Path, url: str, status: str) -> None:
    """把生成结果的 URL 落盘（生成即记，下载成功改标记）。

    下载慢/失败时 URL 不会丢——这正是本次 4K 卡住时暴露的缺口：
    URL 只存在终端输出里，一旦没下完就得翻日志找。
    """
    try:
        data = json.loads(PENDING.read_text(encoding="utf-8")) if PENDING.exists() else []
    except Exception:  # noqa: BLE001
        data = []
    data = [d for d in data if d.get("out") != str(out_p)]
    data.append({"out": str(out_p), "url": url, "status": status,
                 "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    PENDING.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- 局部遮罩（把「改图」插件最强的能力搬进命令行）----------

def build_with_mask(content: Image.Image, mask_path: Path, tw: int, th: int, pad: str,
                    refs: list[Image.Image], invert: bool = False) -> tuple[dict, float]:
    """按给定的蒙版做**任意形状的局部改图**。

    为什么需要它：命令行此前只有 `gen.py --mode mask --protect x0,y0,x1,y1`——**只能给一个保护矩形**，
    表达不了"只重画眼镜""只修一只手"这类需求；而「改图」插件可以随便刷。
    这里把插件那套语义搬过来（复用 `mask_edit_app.make_visual_mask`）：

      · 该接口的 `mask` 字段**被静默忽略**，真正起作用的是把**要改的区域硬涂成纯红**，
        合成成一张图随 `image[1]` 送过去（实测"改区域 100% 生效、保护区完全不动"）；
      · **约定（正向）：蒙版里 alpha=255（或灰度里白色）＝要改的区域**；透明／黑色＝保护不动；
      · **反向（invert=True / CLI `--mask-invert`）：蒙版里白/不透明＝要保护的区域**，
        其余整张图都会被硬涂红、交给模型重建——适合"保住脸与身份像素不动，只重画服装/姿态/背景"，
        **不适合"只改一小块"**（那是正向的用法）；
      · 代价必须记住：硬涂红会**把该区域的原有信息整块抹掉**，模型只能靠提示词与参考图重建。
        所以它适合"要改的区域本来就要把内容清掉"（重画眼睛／手／某一件道具），
        **不适合**"保留结构、整体加色/调浓淡"这类活。
      · 蒙版尺寸不必与内容图一致，会按内容图尺寸重采样；**但内容必须对位**（同一张图的同一块区域）。
    """
    import numpy as np
    from mask_edit_app import make_visual_mask, build_mask_alpha, normalise_to_size

    src = content
    m = Image.open(mask_path)
    if m.size != src.size:
        m = m.resize(src.size, Image.LANCZOS)
    if m.mode == "RGBA":
        cm = m
    else:
        g = np.asarray(m.convert("L"))
        mx = np.zeros((g.shape[0], g.shape[1], 4), np.uint8)
        mx[..., 3] = g
        cm = Image.fromarray(mx, "RGBA")

    vis_png, pad_paint = make_visual_mask(src, cm, tw, th, pad, invert=invert)
    if not pad_paint.any():
        raise SystemExit("  蒙版为空——检查蒙版是不是全黑/全透明（白/不透明＝要改的区域）")
    alpha = build_mask_alpha(pad_paint)

    fit = normalise_to_size(src, tw, th, pad)
    b = io.BytesIO(); fit.save(b, "PNG", optimize=True)
    files = {"image": ("image.png", b.getvalue(), "image/png"),
             "image[1]": ("mask_ref.png", vis_png, "image/png"),
             "mask": ("mask.png", alpha, "image/png")}
    for i, r in enumerate(refs, start=2):
        rb = io.BytesIO(); normalise_to_size(r, tw, th, pad).save(rb, "PNG", optimize=True)
        files[f"image[{i}]"] = (f"ref{i}.png", rb.getvalue(), "image/png")
    return files, float(pad_paint.mean()) * 100


def _fmt_sec(sec: float) -> str:
    return f"{sec:.0f} 秒" if sec < 90 else f"{sec/60:.1f} 分钟"


# 实测投喂上限（MiB）：1.95 通过；2.12 与 2.15 均被 400 form field too large 拒绝。
# 蒙版路径不走压缩梯子，所以它**必须**用这两个数做硬门禁，不能只报警。
LIMIT_OK_MIB, LIMIT_BAD_MIB = 1.96, 2.12


def scratch_path(out_p: Path, suffix: str) -> Path:
    """副产物落盘位置：优先 out 同级的 work/（那里本就是草稿区），没有就放在 out 旁边。"""
    d = out_p.parent / "work"
    if not d.is_dir():
        d = out_p.parent
    return d / f"{out_p.stem}{suffix}"


LEDGER = Path(__file__).resolve().parent / "call_ledger.jsonl"


def log_call(rec: dict) -> None:
    """R1 调用台账：每次调用（含被拒发的）追加一条 JSONL。

    动机（2026-09-22 实测）：原有 pending_urls.json 只记 out/url/status/ts 四个字段，
    没有尺寸、提示词、模型、质量档、HTTP 码——当天两次撞上"无法核实当时到底请求了什么"
    （一次 1254×1254 异常、一次六轮蒙版测试全靠对话记忆复盘）。
    台账只追加、不改历史；写失败**绝不影响作业**。
    """
    try:
        rec = {"ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **rec}
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:                      # 台账永远不该让作业失败
        print(f"  （台账写入失败，已忽略：{e}）", flush=True)


def report_budget(tw: int, th: int, total: int, note: str) -> None:
    """开工前的体积与时间预算报表。

    依据（全部实测）：投喂上限 1.96 MiB 通过 / 4.36 MiB 被拒；
    投喂体积由**目标尺寸**决定、与源图分辨率无关；输出体积 ≈ 像素数 × (1.2–2.0) B/px；
    取回速率实测 0.2–97 KB/s（常见 10–25）。
    """
    LIMIT_OK, LIMIT_BAD = LIMIT_OK_MIB, LIMIT_BAD_MIB      # 见文件上部常量
    px = tw * th
    lo_mb, hi_mb = px * 1.2 / 1048576, px * 2.0 / 1048576
    print("  ── 开工前预算报表 ──")
    print(f"  投喂合计 {total:,} B = {total/1048576:.2f} MiB"
          f"   （实测上限：{LIMIT_OK:.2f} MiB 通过 / {LIMIT_BAD:.2f} MiB 被拒）")
    if total / 1048576 >= LIMIT_BAD:
        print(f"  ✗ 已超上限 → 大概率被拒（400 form field too large）。当前策略：{note}")
    elif total / 1048576 > LIMIT_OK:
        print(f"  ⚠ 处于上限边缘（{LIMIT_OK:.2f}–{LIMIT_BAD:.2f} 之间）→ 可能被拒。策略：{note}")
    elif note and not note.startswith("原样") and "蒙版" not in note:
        print(f"  ⚠ 已触发压缩：{note}")
        print("     → 身份参考可能被抹糊，而**这正是「脸不像」的根源**；能放得下就不要压。")
    else:
        print("  ✓ 未超上限且未压缩（内容与参考保持原样）")
    print(f"  输出 {tw}x{th} = {px/1e6:.2f} Mpx → 预计结果 {lo_mb:.1f}–{hi_mb:.1f} MB")
    print("  取回时间预估：乐观 "
          f"{_fmt_sec(hi_mb*1048576/(90*1024))} / 常见 {_fmt_sec(hi_mb*1048576/(15*1024))}"
          f" / 最坏 {_fmt_sec(hi_mb*1048576/(2*1024))}")
    print("  （最坏档由探测式抢档兜底：低速会被快速淘汰后重试，不会真等这么久）")


# ---------- 单轮 ----------

def run_one(content_p: Path, refs_p: list[Path], prompt_p: Path, out_p: Path,
            tw: int, th: int, pad: str, quality: str, budget: int, check_target: str | None,
            mask_p: Path | None = None, model: str = "", dry_run: bool = False, ask: bool = False,
            mask_invert: bool = False, mask_primary: bool = False) -> int:
    content = Image.open(content_p).convert("RGB")
    refs = [Image.open(p).convert("RGB") for p in refs_p]
    prompt = prompt_p.read_text(encoding="utf-8").strip()

    # R2 比例守卫：--pad 默认 crop 会**静默居中裁掉**源图与目标比例不符的那些边。
    # 2026-09-22 实测踩过：1067×711 的源配 1024×1024 的目标，会被裁掉 33% 的宽度，
    # 而当时没有任何提示，导致一次测试的结论整个跑偏。
    src_ar, tgt_ar = content.width / content.height, tw / th
    if abs(src_ar - tgt_ar) / tgt_ar > 0.02:
        if src_ar > tgt_ar:
            keep = int(content.height * tgt_ar)
            lost, side, px = 1 - keep / content.width, "左右", (content.width - keep) // 2
            alt = "1536x1024" if tgt_ar < 1.4 else "1024x1536"
        else:
            keep = int(content.width / tgt_ar)
            lost, side, px = 1 - keep / content.height, "上下", (content.height - keep) // 2
            alt = "1024x1536" if tgt_ar > 0.75 else "1536x1024"
        print(f"  ⚠ 比例不符：源 {content.width}×{content.height}（{src_ar:.3f}）"
              f" vs 目标 {tw}×{th}（{tgt_ar:.3f}）", flush=True)
        if pad == "crop":
            print(f"     --pad crop 会**居中裁掉 {side}各 {px} px（共 {lost*100:.0f}% 的"
                  f"{'宽度' if src_ar > tgt_ar else '高度'}）**；不想裁就用 `--pad pad`（补白边，"
                  f"代价是画面里出现白边）或把尺寸改成 {alt}", flush=True)
        else:
            print(f"     --pad pad 会**补白边**（{'左右' if src_ar > tgt_ar else '上下'}合计约 "
                  f"{lost*100:.0f}% 的画面是白边）；不想有白边就把尺寸改成 {alt}", flush=True)

    note = "（局部改图模式，蒙版不参与压缩梯子）"
    if mask_p:
        # 局部改图：蒙版本身不参与压缩梯子（它不含视觉信息），只报它的覆盖率
        files, cov = build_with_mask(content, mask_p, tw, th, pad, refs, invert=mask_invert)
        vis_bytes = files["image[1]"][1]
        if mask_primary:
            # 实验：把涂红图当**主图**送（不发干净原图）。机制：抽掉"照抄原图把它恢复"的路径，
            # 顺带把体积砍半（少一张全尺寸图）。若有效则体积门禁问题一并解决。
            files = {"image": ("image.png", vis_bytes, "image/png"),
                     "mask": files["mask"]}
        total = sum(len(v[1]) for v in files.values())
        mode = ("反向：蒙版里涂过的区域**被保留**，其余整张可改" if mask_invert
                else "正向：蒙版里涂过的区域**被修改**，其余像素物理不动")
        print(f"  局部改图模式：{mode}", flush=True)
        print(f"  可改面积 {cov:.1f}%（这部分会被硬涂红，原有信息整块抹掉、交给模型重建）", flush=True)
        if mask_primary:
            print("  --mask-primary：主图就是涂红图（不发干净原图）→ 实测**能产生编辑**（蒙版内改动>120 占 25%）；"
                  "代价是整图会被轻微微调（均值约 5/255），不是逐像素保护", flush=True)
        elif not mask_invert:
            print("  ⚠ 实测（R5 矩阵，2026-09-22）：正向蒙版**不加 --mask-primary** 时，", flush=True)
            print("     模型会照抄原图把那块恢复 → 返回近乎原图（此前 6 次调用全部如此，"
                  "蒙版内最大改动仅 41–59）。", flush=True)
            print("     → **要真的改就用 --mask-primary**；只在你要「验证保护区逐像素没动」时才用这种配置。",
                  flush=True)
        if mask_invert:
            print("    ↳ 反向模式：保护区之外的**整张图**都会重建；"
                  "若只想改一小块，请改用正向遮罩", flush=True)
        if cov > 60:
            print(f"  ⚠ 可改面积达 {cov:.0f}% → 基本等于整图重绘，只有蒙版保护的那部分能保住原像素",
                  flush=True)
        print(f"  发送 {total} B = {total/1048576:.2f} MiB  files={list(files)}", flush=True)
        # 蒙版路径不走压缩梯子（发两张全尺寸图，体积约为单图的两倍）：实测 1536×1024 = 2.15 MiB
        # 会被 400 拒绝、且此前默认不报警。故这里**无条件**报预算，超限直接拒发。
        report_budget(tw, th, total, note)
        red = scratch_path(out_p, ".redmark.png")
        red.write_bytes(vis_bytes)
        print(f"  涂红图（模型收到的 image[1]）已落盘：{red}", flush=True)
        print("    ↳ 发送前请先看一眼红色落在哪一块——落错了位置等于白跑一次调用", flush=True)
        if total / 1048576 > LIMIT_OK_MIB and not dry_run:
            print(f"  ✗ {total/1048576:.2f} MiB 超上限（{LIMIT_OK_MIB} MiB）→ **已拒绝发送**。", flush=True)
            print("     蒙版路径不会自动压缩（它要发两张全尺寸图）。可选：把目标尺寸降到 1024×1024 附近、"
                  "减少参考图、或改用整图 + 硬约束提示词。", flush=True)
            log_call({"out": str(out_p), "size": f"{tw}x{th}", "pad": pad, "quality": quality,
                      "prompt": str(prompt_p),
                      "prompt_sha1": hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12],
                      "content": str(content_p), "n_refs": len(refs_p),
                      "mask": str(mask_p), "mask_invert": mask_invert, "coverage_pct": round(cov, 2),
                      "bytes": total, "http": None, "result": "refused_over_limit",
                      "note": f"{total/1048576:.2f} MiB > {LIMIT_OK_MIB} MiB"})
            return 1
    else:
        c2, r2, note = pick_reduction(content, refs, tw, th, pad, budget)
        print(f"  压缩策略: {note}", flush=True)
        files, _fit = G.build_whole(c2, tw, th, pad, style=r2)
        total = sum(len(v[1]) for v in files.values())
        print(f"  发送 {total} B = {total/1048576:.2f} MiB  files={list(files)}", flush=True)

    if (dry_run or ask) and not mask_p:      # 蒙版分支上面已无条件报过预算，避免重复
        report_budget(tw, th, total, note)
    if dry_run:
        print("  dry-run：**未发送**。确认无误后去掉 --dry-run 并加上 --ask 或直接跑即可。", flush=True)
        return 0
    if ask:
        try:
            ans = input("  是否继续发送？(y/N) ").strip().lower()
        except EOFError:           # 非交互环境（管道/agent）读不到输入 → 视为取消
            ans = ""
        if ans not in ("y", "yes", "是", "继续"):
            print("  已取消发送（未调用接口）。", flush=True)
            return 0

    fields = {"model": model or G.MODEL, "prompt": prompt, "n": "1",
              "size": f"{tw}x{th}", "quality": quality}
    base_rec = {"out": str(out_p), "size": f"{tw}x{th}", "pad": pad, "quality": quality,
                "model": fields["model"], "prompt": str(prompt_p),
                "prompt_sha1": hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12],
                "content": str(content_p), "n_refs": len(refs_p), "bytes": total,
                "fields": list(files),
                "mask": str(mask_p) if mask_p else None,
                "mask_invert": mask_invert if mask_p else None,
                "coverage_pct": round(cov, 2) if mask_p else None}
    t0 = time.time()
    st, txt = post_with_retry(fields, files)
    elapsed = time.time() - t0
    print(f"  HTTP {st}   {elapsed:.1f}s", flush=True)
    if st != 200:
        print("FAILED:\n" + txt[:1200])
        log_call({**base_rec, "http": st, "elapsed_s": round(elapsed, 1),
                  "result": "failed", "error": txt[:300]})
        return 1

    item = (json.loads(txt).get("data") or [{}])[0]
    if item.get("b64_json"):
        out_p.write_bytes(base64.b64decode(item["b64_json"]))
        log_call({**base_rec, "http": st, "elapsed_s": round(elapsed, 1),
                  "result": "b64", "out_bytes": out_p.stat().st_size})
    elif item.get("url"):
        print(f"  result url: {item['url']}", flush=True)   # 先打印再下载
        note_pending(out_p, item["url"], "pending")         # 生成即落盘，下载慢/失败也不丢 URL
        download(item["url"], out_p)
        note_pending(out_p, item["url"], "done")
        log_call({**base_rec, "http": st, "elapsed_s": round(elapsed, 1),
                  "result": "url", "url": item["url"],
                  "out_bytes": out_p.stat().st_size if out_p.exists() else None})
    else:
        print("no image in response: " + txt[:400])
        return 1

    size = Image.open(out_p).size
    print(f"  saved {out_p}  {size}  {out_p.stat().st_size//1024} KB", flush=True)

    if check_target and CHECK.exists():
        print("  --- 生成后体检 ---", flush=True)
        subprocess.run([sys.executable, str(CHECK), "check",
                        "--target", check_target, "--out", str(out_p)])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="一轮作业一键跑")
    ap.add_argument("--content", required=True)
    ap.add_argument("--ref", action="append", default=[], help="可多次；顺序即 image[1]、image[2]…")
    ap.add_argument("--prompt", action="append", required=True)
    ap.add_argument("--out", action="append", required=True)
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--quality", default="low")
    ap.add_argument("--pad", default="crop", choices=["pad", "crop"])
    ap.add_argument("--budget-mib", type=float, default=1.55)
    ap.add_argument("--check-target", default="")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--mask", default="",
                    help="局部改图蒙版（PNG）：白/不透明＝要改的区域，黑/透明＝保护不动。"
                         "走 image[1] 的视觉蒙版通道。"
                         "⚠ **正向改图请配 --mask-primary**（否则实测返回近原图、不会改）。"
                         "⚠ 蒙版路径**不走压缩梯子**：发两张全尺寸图时超 1.96 MiB 会被直接拒发"
                         "（实测 1536×1024 = 2.15 MiB → 400）；配 --mask-primary 只发一张，2K 也放得下")
    ap.add_argument("--mask-invert", action="store_true",
                    help="反向遮罩：蒙版里涂过的区域**被保留**，其余整张可改。"
                         "适合「保住脸/身份不动、只重画服装或姿态或背景」；只改一小块请用正向")
    ap.add_argument("--mask-primary", action="store_true",
                    help="**正向局部改图要用它**：把涂红的视觉蒙版当主图发送（不发干净原图）。"
                         "实测要点：不发干净原图，模型才无法「照抄原图恢复」，才会真的重画那块；"
                         "副作用①整图会被轻微微调（均值约 5/255，非逐像素保护）；"
                         "②体积砍半 → 2K（2048×1152 = 1.29 MiB）也能发")
    ap.add_argument("--model", default="", help="覆盖模型（默认 gpt-image-2；备用通道：grok-imagine-edit）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只做预算报表（投喂体积／是否被压缩／输出体积／取回时间预估），**不发送**")
    ap.add_argument("--ask", action="store_true",
                    help="先打印预算报表，再问 (y/N) 确认才发送。**仅适合交互式手跑**；"
                         "agent/后台请勿用（读不到输入会按取消处理）")
    a = ap.parse_args()

    if len(a.prompt) != len(a.out):
        raise SystemExit("--prompt 与 --out 数量必须一一对应")
    tw, th = (int(v) for v in a.size.split("x"))
    budget = int(a.budget_mib * 1048576)
    mask_p = Path(a.mask) if a.mask else None
    if mask_p and not mask_p.exists():
        raise SystemExit(f"--mask 指定的文件不存在：{mask_p}")

    jobs = [(Path(a.content), [Path(r) for r in a.ref], Path(p), Path(o))
            for p, o in zip(a.prompt, a.out)]

    if len(jobs) == 1 or a.concurrency <= 1:
        rc = 0
        for c, r, p, o in jobs:
            print(f"===== {p.name} -> {o.name} =====", flush=True)
            rc |= run_one(c, r, p, o, tw, th, a.pad, a.quality, budget, a.check_target or None,
                          mask_p=mask_p, model=a.model, dry_run=a.dry_run, ask=a.ask,
                          mask_invert=a.mask_invert, mask_primary=a.mask_primary)
        return rc

    print(f"并行发送 {len(jobs)} 个方案（并发 {a.concurrency}）", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = []
        for c, r, p, o in jobs:
            print(f"  -> {p.name} => {o.name}", flush=True)
            futs.append(ex.submit(run_one, c, r, p, o, tw, th, a.pad, a.quality, budget,
                                  a.check_target or None, mask_p, a.model, a.dry_run, a.ask,
                                  a.mask_invert, a.mask_primary))
        return max(f.result() for f in futs)


if __name__ == "__main__":
    raise SystemExit(main())
