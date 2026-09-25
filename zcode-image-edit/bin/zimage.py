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
import os
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
PY = sys.executable


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


def _run(argv: list[str]) -> int:
    _flush()
    return subprocess.call(argv)


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


# ---------------------------------------------------------------- edit

def cmd_edit(a) -> int:
    image = Path(a.image)
    if not image.is_file():
        raise SystemExit(f"找不到输入图：{image}")
    out = Path(a.out)

    # ---- 凭据前置检查：先失败，别让用户等完压缩才发现没配 key
    # （--dry-run 不发送，所以不要求凭据——否则连预算报表都出不来）
    if not a.dry_run and not _resolved_key():
        print("✗ 未配置 RELAY_API_KEY —— 在花钱之前先停下。")
        print("  PowerShell:  $env:RELAY_API_KEY = 'sk-...'")
        print("  永久:        [Environment]::SetEnvironmentVariable('RELAY_API_KEY','sk-...','User')")
        print("  然后重跑同一命令。凭据只从环境变量读，不写入任何文件。")
        print("  （只想看预算不发送：加 --dry-run）")
        return 2

    # ---- 目标尺寸白名单（跨档组合会被上游拒；文档 B5 已实测）
    sizes = _gen_sizes()
    if a.size not in sizes.get(a.quality, []):
        raise SystemExit(f"--size {a.size} 不在 {a.quality} 档白名单内：{sizes.get(a.quality)}")

    # ---- 区域 → 遮罩
    mask_p = None
    if a.mask_file:
        mask_p = Path(a.mask_file)
        if not mask_p.is_file():
            raise SystemExit(f"找不到遮罩文件：{mask_p}")
        print(f"  用现成遮罩：{mask_p}")
    elif a.whole:
        print("  整图改图模式（不给区域，全图可改）")
    else:
        if not (a.rect or a.polygon or a.flood or a.grabcut is not None):
            raise SystemExit(
                "没有给出要改的区域。三选一：\n"
                "  · 给区域：--rect x0,y0,x1,y1 / --polygon \"x,y x,y x,y\" / --flood x,y[,tol] / --grabcut\n"
                "  · 整图改：--whole\n"
                "  · 手涂遮罩：--mask-file M.png（可用 `zimage.py serve` 打开网页刷）")
        mask_p = out.with_name(out.stem + "-region.png")
        argv = [PY, str(MASKGEN), "--image", str(image), "-o", str(mask_p),
                "--size", a.size, "--pad", a.pad]
        for s in a.rect:
            argv += ["--rect", s]
        for s in a.polygon:
            argv += ["--polygon", s]
        for s in a.flood:
            argv += ["--flood", s]
        if a.grabcut is not None:
            argv += ["--grabcut", a.grabcut]
        if a.dilate:
            argv += ["--dilate", str(a.dilate)]
        print("  ── 生成遮罩 ──")
        rc = _run(argv)
        if rc != 0:
            return rc
        print(f"  遮罩落盘：{mask_p}")

    # ---- 组装并委托 run_round（发送/压缩/重试/下载/校验全在它那里）
    prompt_txt = a.prompt
    if a.prompt_file:
        prompt_txt = Path(a.prompt_file).read_text(encoding="utf-8").strip()
    if not prompt_txt:
        raise SystemExit("必须给 --prompt（或 --prompt-file）")
    pf = out.with_name(out.stem + "-prompt.txt")
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(prompt_txt, encoding="utf-8")

    argv = [PY, str(ROUND), "--content", str(image), "--prompt", str(pf),
            "--out", str(out), "--size", a.size, "--quality", a.quality,
            "--pad", a.pad, "--encode", a.encode]
    for r in a.ref:
        argv += ["--ref", r]
    if mask_p:
        argv += ["--mask", str(mask_p)]
        if a.protect:
            argv += ["--mask-invert"]
            print("  语义：**反向**——你圈的区域会被保护，其余整张重建（不适合「只改一小块」）")
        else:
            print("  语义：**正向**——你圈的区域会被修改，其余像素物理不动")
            if a.no_primary:
                print("  --no-primary：保留干净原图一起发。"
                      "实测这样模型会照抄原图把该块恢复、返回近原图；"
                      "只在你要「验证保护区逐像素没动」时才用。")
            else:
                argv += ["--mask-primary"]
    if a.dry_run:
        argv += ["--dry-run"]
    if a.model:
        argv += ["--model", a.model]

    print("  ── 交给 run_round ──")
    print("  " + " ".join(argv[1:]).replace(str(ROOT) + "\\", "").replace(str(ROOT) + "/", ""))
    rc = _run(argv)

    # ---- 结果确认（不靠肉眼：完整解码 + 报尺寸字节）
    if rc == 0 and out.is_file() and not a.dry_run:
        from PIL import Image
        im = Image.open(out); im.load()
        print(f"\n  ✓ 结果 {out}  {im.size[0]}x{im.size[1]}  {out.stat().st_size / 1024:.0f} KB  完整可解码")
    elif a.dry_run:
        print("\n  （--dry-run：只出了预算报表（给了区域时还有遮罩预览），**没有发送**）")
    return rc


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
    k = os.environ.get("RELAY_API_KEY", "")
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
    e.add_argument("--model", default="")
    e.add_argument("--dry-run", action="store_true", help="只出预算报表与遮罩预览，不发送")
    e.set_defaults(fn=cmd_edit)

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
