#!/usr/bin/env python3
"""zimage —— 在 ZCode 里用的改图工具（不含任何 DSH 依赖）。

它本身**不重写**任何链路：发送/压缩/体积门禁/重试/探测式下载/解码校验全部委托给
`style-distill/round_lib/run_round.py`（那是本项目的实测主力），本脚本只做三件事：
  1. 把"区域规格"变成遮罩 PNG（调 mask_gen.py）——因为 ZCode 里没有涂抹画布；
  2. 凭据与前置检查（在花钱之前就失败，而不是跑到一半才发现没配 key）；
  3. 把本地服务（网页手涂 / 画廊）拉起、打开、停掉——替掉 DSH 插件那个"按钮"。

子命令：
  edit      改图：区域→遮罩→调用接口→落盘（默认先给预览，可 --dry-run 不发送）
  local     确定性本地操作（线稿调淡/放大/裁切/拼版/调子剖面），不调接口
  serve     拉起网页手涂页并打开浏览器
  gallery   拉起画廊页并打开浏览器
  stop      停掉上面拉起的服务
  doctor    自检：依赖、凭据、脚本就位、ZCode 存储、技能安装状态（不调接口）

凭据只从环境变量读：RELAY_API_KEY（必填）/ RELAY_BASE_URL / RELAY_MODEL。
"""
from __future__ import annotations
import sys as _sys

# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
# 注意顺序：若本文件将来引入 from __future__，它必须是第一条语句。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PKG = _HERE.parent                      # zcode-image-edit/


def find_root() -> Path:
    """定位工作区根目录。

    不写死"往上两层"——那样换布局就断。优先 ZIMAGE_ROOT，否则从本文件往上找
    同时含 compose/images/mask_edit_app.py 与 style-distill/round_lib/run_round.py 的目录。
    """
    env = os.environ.get("ZIMAGE_ROOT")
    if env:
        p = Path(env)
        if not p.is_dir():
            raise SystemExit(f"ZIMAGE_ROOT 指向的目录不存在：{p}")
        return p.resolve()
    for cand in [_HERE, *_HERE.parents]:
        if (cand / "compose" / "images" / "mask_edit_app.py").is_file() and \
           (cand / "style-distill" / "round_lib" / "run_round.py").is_file():
            return cand
    raise SystemExit(
        "找不到工作区根目录（需含 compose/images/mask_edit_app.py 与 "
        "style-distill/round_lib/run_round.py）。请设 ZIMAGE_ROOT 指过去。")


ROOT = find_root()
APP = ROOT / "compose" / "images" / "mask_edit_app.py"
ROUND = ROOT / "style-distill" / "round_lib" / "run_round.py"
LOCAL = ROOT / "style-distill" / "round_lib" / "local_ops.py"
MASKGEN = PKG / "mask_gen.py"
RELIABILITY = PKG / "reliability.py"
PY = sys.executable

sys.path.insert(0, str(PKG))
import reliability as R  # noqa: E402


# ---------------------------------------------------------------- 工具

def _pidfile(port: int) -> Path:
    return Path(tempfile.gettempdir()) / f"zimage-service-{port}.pid"


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket(); s.settimeout(1.0)
    try:
        s.connect((host, port)); return True
    except Exception:
        return False
    finally:
        s.close()


def _http_ok(url: str, timeout: float = 8.0) -> int:
    """用 urllib 取状态码；失败返回 0。

    ⚠ 不要用 `fetch` 那种"请求后立刻 abort"的探活方式去探测以 HTTP/1.0 应答的本服务——
    文档 B3 记过一次实测：那会在 undici 内部抛不可捕获断言、直接杀掉宿主进程。
    这里是独立的 Python 进程，用 urllib 正常读完整响应，安全。
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read(64)
            return int(r.status)
    except Exception:
        return 0


def _open_browser(url: str) -> None:
    try:
        if os.name == "nt":
            os.startfile(url)          # noqa: S606
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception as e:
        print(f"  （自动打开浏览器失败：{type(e).__name__}: {e}；请手动打开 {url}）")


def _flush() -> None:
    """子进程直接写终端，但父进程的 stdout 被管道缓冲——不先 flush 自己的，
    子进程的输出就会插到前面，日志顺序乱掉。每次 spawn 之前都要调。"""
    for s in (sys.stdout, sys.stderr):
        try:
            s.flush()
        except Exception:
            pass


def _run(argv: list[str], *, capture: bool = False, cwd: Path | None = None) -> tuple[int, str] | int:
    _flush()
    if not capture:
        return subprocess.call(argv, cwd=str(cwd) if cwd else None)
    p = subprocess.Popen(argv, cwd=str(cwd) if cwd else None,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", bufsize=1)
    chunks: list[str] = []
    assert p.stdout is not None
    for line in p.stdout:
        print(line, end="", flush=True)
        chunks.append(line)
    return p.wait(), "".join(chunks)


def _resolved_key() -> str:
    """与 gen.py 同一套凭据解析（进程环境 → 用户级注册表回退）。

    不能直接读 os.environ：进程的环境块是启动时固定的，若 ZCode 早于环境变量设置而启动，
    这里会报"未配置"而 gen.py 却能拿到凭据——出现自相矛盾的假阴性。
    """
    try:
        sys.path.insert(0, str(APP.parent))
        import gen  # noqa: E402
        return gen.KEY
    except Exception:
        return os.environ.get("RELAY_API_KEY", "")


def _gen_sizes() -> dict:
    """从 gen.py 读尺寸白名单——单一事实来源，避免这里再抄一份导致漂移。"""
    sys.path.insert(0, str(APP.parent))
    import gen  # noqa: E402
    return gen.SIZES


def _resolved_endpoint() -> str:
    sys.path.insert(0, str(APP.parent))
    import gen  # noqa: E402
    return gen.BASE


def _resolved_model() -> str:
    sys.path.insert(0, str(APP.parent))
    import gen  # noqa: E402
    return gen.MODEL


# ---------------------------------------------------------------- reliability

RELIABILITY_STATES = {
    "created", "preflight_ok", "prepared", "submitted", "retrying",
    "received", "decoded", "validated", "cache_hit", "saved", "failed", "blocked",
}


def _cache_root() -> Path:
    value = os.environ.get("ZIMAGE_CACHE_DIR", "")
    return Path(value).expanduser().resolve() if value else ROOT / ".zimage" / "cache"


def _job_dir(job: str) -> Path:
    d = ROOT / ".zimage" / "jobs" / job
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_state(path: Path, state: str, **extra) -> None:
    if state not in RELIABILITY_STATES:
        raise ValueError(state)
    data = {"state": state, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **extra}
    R.write_manifest(path, data)


def _read_prompt(a) -> str:
    prompt = a.prompt
    if a.prompt_file:
        prompt = Path(a.prompt_file).read_text(encoding="utf-8").strip()
    if not prompt:
        raise SystemExit("必须给 --prompt（或 --prompt-file）")
    return prompt


def _validate_input(image: Path) -> tuple[int, int]:
    if not image.is_file():
        raise SystemExit(f"找不到输入图：{image}")
    from PIL import Image
    try:
        im = Image.open(image); im.load()
    except Exception as e:
        raise SystemExit(f"输入图无法完整解码：{image}: {e}")
    if im.width < 16 or im.height < 16:
        raise SystemExit(f"输入图尺寸过小：{im.size}")
    return im.size


def _prepare_mask(a, image: Path, dst: Path) -> Path | None:
    import shutil
    if a.mask_file:
        src = Path(a.mask_file)
        if not src.is_file():
            raise SystemExit(f"找不到遮罩文件：{src}")
        shutil.copy2(src, dst)
        return dst
    if a.whole:
        return None
    if not (a.rect or a.polygon or a.flood or a.grabcut is not None):
        raise SystemExit(
            "没有给出要改的区域。请用 --rect/--polygon/--flood/--grabcut，"
            "或 --whole，或 --mask-file。")
    argv = [PY, str(MASKGEN), "--image", str(image), "-o", str(dst)]
    for x in a.rect:
        argv += ["--rect", x]
    for x in a.polygon:
        argv += ["--polygon", x]
    for x in a.flood:
        argv += ["--flood", x]
    if a.grabcut is not None:
        argv += ["--grabcut", a.grabcut]
    if a.dilate:
        argv += ["--dilate", str(a.dilate)]
    rc = _run(argv)
    if rc:
        raise SystemExit(rc)
    return dst


def _mask_summary(source: Path, mask: Path, *, protect: bool) -> tuple[float, list[str]]:
    from PIL import Image
    import numpy as np
    src = Image.open(source); src.load()
    m = Image.open(mask); m.load()
    warnings: list[str] = []
    if m.size != src.size:
        raise SystemExit(f"遮罩尺寸 {m.size} 与源图 {src.size} 不同；请先对齐，不静默重采样")
    alpha = np.asarray(m.convert("RGBA").getchannel("A")) > 127
    ratio = float(alpha.mean())
    if not ratio:
        raise SystemExit("遮罩为空：alpha=255 的区域为 0")
    if ratio < 0.001:
        warnings.append(f"遮罩面积 {ratio * 100:.3f}% 过小，可能几乎没有可见修改")
    if ratio > 0.80:
        warnings.append(f"遮罩面积 {ratio * 100:.1f}% 过大，接近整图重绘")
    if protect:
        warnings.append("反向语义：圈中区域保护，圈外整张重建")
    return ratio, warnings


def _estimate_bytes(image: Path, mask: Path | None, refs: list[str], a,
                    *, mask_primary: bool = False) -> tuple[int | None, float | None]:
    """本地估算真实请求体，不发送。

    局部路径按实际 image/mask 载荷算；整图路径复用 run_round 的 JPEG/压缩梯子，
    这样 plan 输出的数字与后面 dry-run 的口径一致。
    """
    from PIL import Image
    sys.path.insert(0, str(ROUND.parent))
    import run_round as rr
    src = Image.open(image).convert("RGB")
    ref_imgs = [Image.open(x).convert("RGB") for x in refs]
    tw, th = (int(x) for x in a.size.split("x"))
    if mask:
        files, coverage = rr.build_with_mask(src, mask, tw, th, a.pad, ref_imgs, invert=a.protect)
        if mask_primary:
            total = len(files["image[1]"][1]) + len(files["mask"][1])
        else:
            total = sum(len(v[1]) for v in files.values())
        return total, coverage
    if getattr(a, "encode", "png") == "jpg":
        files = rr.build_jpg(src, ref_imgs, tw, th, a.pad, getattr(a, "jpg_quality", 90))
        return sum(len(v[1]) for v in files.values()), None
    c2, r2, _note = rr.pick_reduction(src, ref_imgs, tw, th, a.pad,
                                       int(getattr(a, "budget_mib", 1.55) * 1048576))
    total = rr.norm_bytes(c2, tw, th, a.pad) + sum(rr.norm_bytes(r, tw, th, a.pad) for r in r2)
    return total, None


def _validate_refs(refs: list[str]) -> list[str]:
    out = []
    for ref in refs:
        p = Path(ref)
        if not p.is_file():
            raise SystemExit(f"找不到参考图：{p}")
        _validate_input(p)
        out.append(str(p.resolve()))
    return out


def _classify_failure(output: str, rc: int) -> str:
    low = output.lower()
    if "moderation" in low or "审核" in output:
        return "moderation_blocked"
    if "401" in low or "api key" in low or "apikey" in low:
        return "auth_error"
    if "timeout" in low or "timed out" in low:
        return "timeout"
    if any(x in low for x in ("502", "503", "504")):
        return "network_error"
    if "解码" in output or "truncated" in low or "not an image" in low:
        return "invalid_image"
    return "unknown" if rc else "failed"


def _plan_data(a, *, persist_mask: Path | None = None) -> tuple[dict, Path | None]:
    image = Path(a.image).resolve()
    source_size = _validate_input(image)
    prompt = _read_prompt(a)
    a.ref = _validate_refs(a.ref)
    sizes = _gen_sizes()
    if a.size not in sizes.get(a.quality, []):
        raise SystemExit(f"--size {a.size} 不在 {a.quality} 档白名单内：{sizes.get(a.quality)}")
    mask = persist_mask
    temp_dir = None
    if persist_mask is not None and (a.mask_file or not a.whole):
        mask = _prepare_mask(a, image, persist_mask)
    elif mask is None and (a.mask_file or not a.whole):
        temp_dir = Path(tempfile.mkdtemp(prefix="zimage-plan-"))
        mask = _prepare_mask(a, image, temp_dir / "mask.png")
    if mask:
        ratio, warnings = _mask_summary(image, mask, protect=a.protect)
    else:
        ratio, warnings = None, []
    mask_primary = bool(mask and not a.protect and not getattr(a, "no_primary", False))
    fp = R.request_fingerprint(source=image, mask=mask, prompt=prompt,
                               model=a.model or _resolved_model(), size=a.size,
                               quality=a.quality, pad=a.pad, mask_invert=a.protect,
                               refs=[Path(x) for x in a.ref], encode=getattr(a, "encode", "png"),
                               jpg_quality=getattr(a, "jpg_quality", 90),
                               budget_mib=getattr(a, "budget_mib", 1.55),
                               endpoint=_resolved_endpoint(),
                               mask_primary=mask_primary)
    estimated, coverage = _estimate_bytes(
        image, mask, a.ref, a, mask_primary=mask_primary
    ) if mask else (None, None)
    if mask and a.protect:
        warnings.append("反向保护模式不使用 mask-primary：保护语义就是保留圈内原像素")
    if temp_dir is not None:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    data = {
        "job_id": getattr(a, "job_id", "") or R.job_id(),
        "source": str(image),
        "source_size": list(source_size),
        "mask": str(mask) if mask else None,
        "mask_mode": "protect" if a.protect else ("edit" if mask else "whole"),
        "mask_ratio": ratio,
        "coverage_target_ratio": coverage,
        "model": a.model or _resolved_model(),
        "size": a.size,
        "quality": a.quality,
        "pad": a.pad,
        "prompt_sha256": R.sha256_text(R.normalize_prompt(prompt)),
        "fingerprint": fp,
        "estimated_request_bytes": estimated,
        "warnings": warnings,
        "status": "preflight_ok",
    }
    return data, mask


def cmd_plan(a) -> int:
    """纯本地计划：图片/遮罩/尺寸/指纹/预算，绝不调用上游。"""
    data, mask = _plan_data(a)
    print("== zimage plan（本地，不发送）==")
    print("  job_id     :", data["job_id"])
    print("  源图       :", data["source"])
    print("  源图尺寸   :", "x".join(map(str, data["source_size"])))
    print("  任务       :", data["mask_mode"])
    print("  目标尺寸   :", data["size"], "质量:", data["quality"], "pad:", data["pad"])
    print("  模型       :", data["model"])
    print("  prompt sha  :", data["prompt_sha256"][:16])
    print("  fingerprint :", data["fingerprint"])
    print("  请求体估算 :", f"{data['estimated_request_bytes']:,} B" if data["estimated_request_bytes"] else "整图路径由 run_round dry-run 精算")
    print("  修改面积   :", f"{data['mask_ratio'] * 100:.1f}%" if data["mask_ratio"] is not None else "整图")
    print("  状态       : preflight_ok（计划可提交；仍需 dry-run 预算）")
    for w in data["warnings"]:
        print("  ⚠", w)
    return 0


def cmd_edit(a) -> int:
    image = Path(a.image).resolve()
    _validate_input(image)
    prompt_txt = _read_prompt(a)
    a.ref = _validate_refs(a.ref)
    out = Path(a.out).resolve()
    if out.exists() and not a.force:
        raise SystemExit(f"输出已存在（加 --force 才覆盖）：{out}")

    job = a.job_id or R.job_id()
    if not re.match(r"^[A-Za-z0-9_.-]+$", job):
        raise SystemExit("--job-id 只能包含字母、数字、点、下划线、连字符")
    jd = _job_dir(job)
    manifest = jd / "manifest.json"
    print(f"  job_id  : {job}")
    print(f"  manifest: {manifest}")
    _write_state(manifest, "created", job_id=job, source=str(image), status="created")
    try:
        mask = _prepare_mask(a, image, jd / "mask.png")
        ratio, warnings = _mask_summary(image, mask, protect=a.protect) if mask else (None, [])
        prompt_file = jd / "prompt.txt"
        R.atomic_write_text(prompt_file, prompt_txt)
        mask_primary = bool(mask and not a.protect and not getattr(a, "no_primary", False))
        fp = R.request_fingerprint(source=image, mask=mask, prompt=prompt_txt,
                                   model=a.model or _resolved_model(), size=a.size,
                                   quality=a.quality, pad=a.pad, mask_invert=a.protect,
                                   refs=[Path(x) for x in a.ref], encode=a.encode,
                                   jpg_quality=getattr(a, "jpg_quality", 90),
                                   budget_mib=a.budget_mib,
                                   endpoint=_resolved_endpoint(),
                                   mask_primary=mask_primary)
        estimated, coverage = _estimate_bytes(
            image, mask, a.ref, a, mask_primary=mask_primary
        ) if mask else (None, None)
        if mask and a.protect:
            warnings.append("反向保护模式不使用 mask-primary：保护语义就是保留圈内原像素")
        R.update_manifest(manifest, job_id=job, state="preflight_ok", status="preflight_ok",
                          source_sha256=R.sha256_file(image),
                          mask_sha256=R.sha256_file(mask) if mask else None,
                          prompt_sha256=R.sha256_text(R.normalize_prompt(prompt_txt)),
                          model=a.model or _resolved_model(), size=a.size, quality=a.quality,
                          pad=a.pad, mask_mode=("protect" if a.protect else ("edit" if mask else "whole")),
                          mask_ratio=ratio, coverage_target_ratio=coverage,
                          request_fingerprint=fp, warnings=warnings)
        R.update_manifest(manifest, state="prepared", status="prepared")

        cache = None if a.no_cache or a.dry_run else R.load_valid_cache(_cache_root(), fp)
        if cache is not None:
            cached_result = Path(cache["result_path"])
            R.atomic_copy(cached_result, out, force=a.force)
            R.update_manifest(manifest, state="cache_hit", status="cache_hit",
                              cache_dir=str(_cache_root()), cached_result_sha256=cache.get("result_sha256"),
                              output=str(out), result_size=cache.get("result_size"),
                              validation=cache.get("validation"))
            R.update_manifest(manifest, state="saved", status="saved", output=str(out), from_cache=True)
            print(f"✓ 缓存命中：{fp} → {out}  （未发送上游）")
            return 0
        if not a.dry_run and not _resolved_key():
            R.update_manifest(manifest, state="blocked", status="auth_error", failure_type="auth_error")
            print("✗ 未配置 RELAY_API_KEY —— 在花钱之前先停下。")
            return 2

        temp_out = jd / "result.tmp.png"
        argv = [PY, str(ROUND), "--content", str(image), "--prompt", str(prompt_file),
                "--out", str(temp_out), "--size", a.size, "--quality", a.quality,
                "--pad", a.pad, "--encode", a.encode, "--budget-mib", str(a.budget_mib)]
        for r in a.ref:
            argv += ["--ref", r]
        if mask:
            argv += ["--mask", str(mask)]
            if a.protect:
                argv += ["--mask-invert"]
            elif not a.no_primary:
                argv += ["--mask-primary"]
        if a.dry_run:
            argv += ["--dry-run"]
        if a.model:
            argv += ["--model", a.model]
        R.update_manifest(manifest, state="submitted", status="submitted",
                          request_bytes=estimated, attempts=1)
        rc, log = _run(argv, capture=True)
        R.atomic_write_text(jd / "process.log", log)
        retry_lines = [x for x in log.splitlines() if "发送第" in x and "/" in x]
        if retry_lines:
            import re as _re
            nums = [_re.search(r"发送第\s+(\d+)/(\d+)", x) for x in retry_lines]
            attempts = max((int(m.group(1)) for m in nums if m), default=1)
            R.update_manifest(manifest, state="retrying", status="retrying", attempts=attempts)
        if a.dry_run:
            R.update_manifest(manifest, state="prepared", status="plan_only", dry_run=True)
            return rc
        if rc != 0:
            failure = _classify_failure(log, rc)
            R.update_manifest(manifest, state="blocked" if failure == "moderation_blocked" else "failed",
                              status=failure, failure_type=failure)
            return rc
        R.update_manifest(manifest, state="received", status="received")
        if not temp_out.is_file():
            R.update_manifest(manifest, state="failed", status="invalid_image", failure_type="invalid_image")
            print("✗ 上游返回成功但没有结果文件")
            return 3
        from PIL import Image
        try:
            im = Image.open(temp_out); im.load()
        except Exception as e:
            R.update_manifest(manifest, state="failed", status="invalid_image", failure_type="invalid_image",
                              error=str(e))
            print("✗ 结果图片无法完整解码：", e)
            return 3
        R.update_manifest(manifest, state="decoded", status="decoded",
                          result_size=list(im.size), result_bytes=temp_out.stat().st_size)
        metrics = None
        if mask:
            metrics = R.protection_metrics(image, temp_out, mask,
                                           requested_size=a.size, pad=a.pad, invert=a.protect)
            R.update_manifest(manifest, state="validated", status=metrics["status"], validation=metrics)
            print("结果验收：", json.dumps(metrics, ensure_ascii=False))
            if metrics["status"] == "FAIL":
                R.update_manifest(manifest, state="failed", status="protected_area_changed",
                                  failure_type="protected_area_changed")
                print("✗ 遮罩验收失败；结果保留在 Job 目录，没有替换最终输出")
                return 4
        else:
            R.update_manifest(manifest, state="validated", status="PASS", validation={"status": "PASS"})
        R.atomic_replace(temp_out, out, force=a.force)
        cache_warning = None
        try:
            cached = None if a.no_cache else R.store_cache(
                _cache_root(), fp, out,
                result_size=list(im.size), validation=metrics or {"status": "PASS"})
            cache_warning = None
        except Exception as cache_error:
            cached = None
            cache_warning = f"缓存写入失败：{type(cache_error).__name__}: {cache_error}"
            print("⚠", cache_warning)
        R.update_manifest(manifest, state="saved", status="saved", output=str(out),
                          cache_stored=bool(cached), cache_warning=cache_warning)
        print(f"✓ 结果原子写入：{out}  {im.size[0]}x{im.size[1]}  {out.stat().st_size / 1024:.0f} KB")
        return 0
    except BaseException as e:
        if isinstance(e, SystemExit):
            R.update_manifest(manifest, state="failed", status="failed", error=str(e))
            raise
        R.update_manifest(manifest, state="failed", status="failed", error=f"{type(e).__name__}: {e}")
        raise

# ---------------------------------------------------------------- 本地服务

def _start_service(port: int, detach: bool) -> subprocess.Popen | None:
    """已在跑就直接用；否则拉起。返回新进程（已在跑时返回 None）。"""
    if _port_open(port):
        print(f"  服务已在 127.0.0.1:{port} 运行，直接复用")
        return None
    popen_kw = dict(cwd=str(APP.parent), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if detach and os.name == "nt":
        popen_kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS|NEW_PROCESS_GROUP
    elif detach:
        popen_kw["start_new_session"] = True
    proc = subprocess.Popen([PY, str(APP), "--port", str(port)], **popen_kw)
    _pidfile(port).write_text(str(proc.pid), encoding="utf-8")
    for _ in range(30):
        if _port_open(port):
            print(f"  服务已起于 127.0.0.1:{port}（pid {proc.pid}）")
            return proc
        time.sleep(0.4)
    print(f"  ✗ 服务 12 秒内没起来（pid {proc.pid}）")
    print(f"    自检：{PY} \"{APP}\" --port {port}   ← 直接前台跑会打印原因")
    return proc


def _serve(a, path: str) -> int:
    url = f"http://127.0.0.1:{a.port}{path}"
    proc = _start_service(a.port, detach=not a.foreground)
    code = _http_ok(url)
    print(f"  GET {url} → HTTP {code}" + (" ✓" if code == 200 else " ✗"))
    if code == 200 and not a.no_open:
        _open_browser(url)
        print(f"  已尝试打开浏览器：{url}")
    if a.foreground and proc is not None:
        print("  前台运行中，Ctrl+C 结束")
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
        return 0
    print(f"  后台运行中。停止：python zimage.py stop --port {a.port}")
    return 0 if code == 200 else 1


def cmd_serve(a) -> int:
    return _serve(a, "/")


def cmd_gallery(a) -> int:
    return _serve(a, "/gallery")


def cmd_stop(a) -> int:
    pf = _pidfile(a.port)
    if not pf.is_file():
        print(f"  没有 pid 记录（{pf}）；端口{'在听' if _port_open(a.port) else '也没在听'}")
        return 0
    pid = pf.read_text(encoding="utf-8").strip()
    print(f"  停止 pid {pid}（端口 {a.port}）")
    if os.name == "nt":
        subprocess.call(["taskkill", "/PID", pid, "/F"], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
    else:
        try:
            os.kill(int(pid), 15)
        except Exception as e:
            print("  kill 失败:", e)
    time.sleep(1.0)
    print("  端口仍在听:", _port_open(a.port))
    if not _port_open(a.port):
        pf.unlink(missing_ok=True)
    return 0


# ---------------------------------------------------------------- doctor

def cmd_doctor(a) -> int:
    print("== zimage 自检 ==")
    print(f"  Python        : {sys.version.split()[0]}  ({PY})")
    print(f"  工作区根      : {ROOT}")

    print("\n  [依赖]")
    for m in ("PIL", "numpy", "cv2"):
        try:
            mod = __import__(m)
            print(f"    {m:8s} OK  {getattr(mod, '__version__', '?')}")
        except Exception as e:
            print(f"    {m:8s} **缺失** {type(e).__name__}")

    print("\n  [凭据]（只看有没有，不打印值）")
    k = _resolved_key()
    print(f"    RELAY_API_KEY  : {'已设置（%d 字符）' % len(k) if k else '**未设置** → edit 会直接停下'}")

    sys.path.insert(0, str(APP.parent))
    try:
        import gen
        print(f"    RELAY_BASE_URL : {gen.BASE}")
        print(f"    RELAY_MODEL    : {gen.MODEL}")
    except Exception as e:
        print("    gen.py 导入失败:", e)

    print("\n  [脚本就位]")
    for label, p in (("服务本体 mask_edit_app.py", APP), ("一键跑一轮 run_round.py", ROUND),
                     ("本地操作 local_ops.py", LOCAL), ("遮罩生成 mask_gen.py", MASKGEN)):
        print(f"    {label:28s} {'✓' if p.is_file() else '**缺失**'}  {p}")

    print("\n  [本地服务]")
    for port in (8000, 3080):
        print(f"    {port} {'在听' if _port_open(port) else '未听'}")

    print("\n  [ZCode 存储]（画廊「输入」页签的数据源）")
    zc = Path.home() / ".zcode" / "cli"
    print(f"    db.sqlite   {'✓' if (zc / 'db' / 'db.sqlite').is_file() else '**缺失**'}  {zc / 'db' / 'db.sqlite'}")
    print(f"    artifacts/  {'✓' if (zc / 'artifacts').is_dir() else '**缺失**'}  {zc / 'artifacts'}")

    print("\n  [技能与命令安装状态]")
    sk = Path.home() / ".agents" / "skills" / "image-edit" / "SKILL.md"
    mirror = PKG / "_skill" / "image-edit" / "SKILL.md"
    if sk.is_file() and mirror.is_file():
        import hashlib
        h1 = hashlib.sha256(sk.read_bytes()).hexdigest()[:12]
        h2 = hashlib.sha256(mirror.read_bytes()).hexdigest()[:12]
        print(f"    技能已装      {sk}")
        print(f"    与镜像一致    {'✓' if h1 == h2 else '**不同**（重跑 install.py）'}  {h1} / {h2}")
    elif mirror.is_file():
        print(f"    技能**未装**（镜像在 {mirror}）→ 跑 python zimage.py install 装上")
    else:
        print("    技能既未装、镜像也缺 —— 先确认 zcode-image-edit/_skill/image-edit/ 存在")
    cdir = Path.home() / ".agents" / "commands"
    for c in ("image-edit.md", "paint-mask.md", "image-gallery.md"):
        print(f"    命令 /{c[:-3]:14s} {'✓' if (cdir / c).is_file() else '**未装**'}")
    return 0


def cmd_local(a) -> int:
    argv = [PY, str(LOCAL)] + list(a.rest)
    return _run(argv)


def cmd_install(a) -> int:
    """转发给 install.py：装技能与命令到 ZCode 用户作用域并自检。"""
    argv = [PY, str(PKG / "install.py")] + list(a.rest)
    return _run(argv)


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="ZCode 里的改图工具（委托 run_round，无 DSH 依赖）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("edit", help="改图：区域→遮罩→调接口→落盘")
    e.add_argument("--image", required=True)
    e.add_argument("--prompt", default="", help="要改成的样子（一句话）")
    e.add_argument("--prompt-file", default="")
    e.add_argument("--out", required=True)
    e.add_argument("--ref", action="append", default=[], help="参考图（可重复，映射 image[1..]）")
    e.add_argument("--rect", action="append", default=[], help="x0,y0,x1,y1（可重复取并集）")
    e.add_argument("--polygon", action="append", default=[], help="x,y x,y x,y …")
    e.add_argument("--flood", action="append", default=[], help="x,y[,tol] 种子点漫水")
    e.add_argument("--grabcut", nargs="?", const="", default=None, help="前景分割（可选初始框）")
    e.add_argument("--dilate", type=int, default=0, help="区域外扩 N 像素")
    e.add_argument("--mask-file", default="", help="用现成遮罩 PNG（alpha=255 即圈中区域）")
    e.add_argument("--protect", action="store_true", help="反向：圈中的区域被**保护**")
    e.add_argument("--no-primary", action="store_true",
                   help="正向时不加 --mask-primary（仅用于验证保护区逐像素未动）")
    e.add_argument("--whole", action="store_true", help="整图改图，不给区域")
    e.add_argument("--size", default="1024x1536")
    e.add_argument("--quality", default="low", choices=["low", "medium", "high"])
    e.add_argument("--pad", default="crop", choices=["pad", "crop"])
    e.add_argument("--encode", default="png", choices=["png", "jpg"])
    e.add_argument("--jpg-quality", type=int, default=90)
    e.add_argument("--model", default="")
    e.add_argument("--budget-mib", type=float, default=1.55)
    e.add_argument("--dry-run", action="store_true", help="只出预算报表与遮罩预览，不发送")
    e.add_argument("--force", action="store_true", help="允许覆盖已有输出")
    e.add_argument("--no-cache", action="store_true", help="不读取或写入成功结果缓存")
    e.add_argument("--job-id", default="", help="显式指定可复现的 job id")
    e.set_defaults(fn=cmd_edit)

    pl = sub.add_parser("plan", help="只做本地预检与请求计划，不调用上游")
    pl.add_argument("--image", required=True)
    pl.add_argument("--prompt", default="")
    pl.add_argument("--prompt-file", default="")
    pl.add_argument("--ref", action="append", default=[])
    pl.add_argument("--rect", action="append", default=[])
    pl.add_argument("--polygon", action="append", default=[])
    pl.add_argument("--flood", action="append", default=[])
    pl.add_argument("--grabcut", nargs="?", const="", default=None)
    pl.add_argument("--dilate", type=int, default=0)
    pl.add_argument("--mask-file", default="")
    pl.add_argument("--protect", action="store_true")
    pl.add_argument("--whole", action="store_true")
    pl.add_argument("--size", default="1024x1536")
    pl.add_argument("--quality", default="low", choices=["low", "medium", "high"])
    pl.add_argument("--pad", default="crop", choices=["pad", "crop"])
    pl.add_argument("--encode", default="png", choices=["png", "jpg"])
    pl.add_argument("--jpg-quality", type=int, default=90)
    pl.add_argument("--budget-mib", type=float, default=1.55)
    pl.add_argument("--model", default="")
    pl.add_argument("--no-primary", action="store_true")
    pl.set_defaults(fn=cmd_plan)

    s = sub.add_parser("serve", help="拉起网页手涂页")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--foreground", action="store_true", help="前台运行（Ctrl+C 结束）")
    s.add_argument("--no-open", action="store_true")
    s.set_defaults(fn=cmd_serve)

    g = sub.add_parser("gallery", help="拉起画廊页")
    g.add_argument("--port", type=int, default=8000)
    g.add_argument("--foreground", action="store_true")
    g.add_argument("--no-open", action="store_true")
    g.set_defaults(fn=cmd_gallery)

    t = sub.add_parser("stop", help="停掉上面拉起的服务")
    t.add_argument("--port", type=int, default=8000)
    t.set_defaults(fn=cmd_stop)

    d = sub.add_parser("doctor", help="自检（不调接口）")
    d.set_defaults(fn=cmd_doctor)

    lo = sub.add_parser("local", help="确定性本地操作（转发 local_ops.py）")
    lo.add_argument("rest", nargs=argparse.REMAINDER)
    lo.set_defaults(fn=cmd_local)

    ins = sub.add_parser("install", help="装技能与命令到 ZCode 用户作用域（转发 install.py）")
    ins.add_argument("rest", nargs=argparse.REMAINDER)
    ins.set_defaults(fn=cmd_install)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
