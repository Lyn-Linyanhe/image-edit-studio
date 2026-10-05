#!/usr/bin/env python3
"""MCP: start/stop/status/open the local image-edit canvas. Secrets stay in the page."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PLUGIN_ROOT = Path(os.environ.get("IMAGE_EDIT_PLUGIN_ROOT") or Path(__file__).resolve().parents[1])
SERVER_SCRIPT = PLUGIN_ROOT / "server" / "mask_edit_app.py"
PID_FILE = PLUGIN_ROOT / ".image-edit.pid"
LOG_FILE = PLUGIN_ROOT / "server.log"
DEFAULT_PORT = int(os.environ.get("IMAGE_EDIT_PORT") or "8000")

mcp = FastMCP("image-edit")


def _port() -> int:
    try:
        return int(os.environ.get("IMAGE_EDIT_PORT") or DEFAULT_PORT)
    except ValueError:
        return DEFAULT_PORT


def _url(port: int | None = None) -> str:
    return "http://127.0.0.1:%d/" % (port or _port())


def _read_pid() -> tuple[int | None, int | None]:
    if not PID_FILE.exists():
        return None, None
    try:
        lines = PID_FILE.read_text(encoding="utf-8").strip().splitlines()
        pid = int(lines[0]) if lines else None
        port = int(lines[1]) if len(lines) > 1 else _port()
        return pid, port
    except (OSError, ValueError):
        return None, None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _probe(port: int, timeout: float = 1.5) -> dict:
    url = "http://127.0.0.1:%d/health" % port
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {"raw": raw}
            return {"ok": resp.status == 200, "status": resp.status, "body": body}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _python() -> str:
    return sys.executable


def _spawn(port: int) -> int:
    if not SERVER_SCRIPT.is_file():
        raise FileNotFoundError("找不到本地服务脚本: %s" % SERVER_SCRIPT)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_fp = open(LOG_FILE, "a", encoding="utf-8")
    creationflags = 0
    kwargs = {
        "args": [_python(), str(SERVER_SCRIPT), "--port", str(port)],
        "cwd": str(SERVER_SCRIPT.parent),
        "stdout": log_fp,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
        kwargs["creationflags"] = creationflags
        kwargs["close_fds"] = False
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(**kwargs)
    return proc.pid


def _wait_up(port: int, timeout_s: float = 25.0) -> dict:
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout_s:
        last = _probe(port)
        if last.get("ok"):
            return last
        time.sleep(0.25)
    return last or {"ok": False, "error": "启动超时"}


def _kill(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
        return
    try:
        os.kill(pid, 15)
    except OSError:
        pass


def status_payload() -> dict:
    pid, port = _read_pid()
    port = port or _port()
    probe = _probe(port)
    alive = bool(pid and _pid_alive(pid))
    running = bool(probe.get("ok"))
    return {
        "running": running,
        "pid": pid if (alive or running) else None,
        "port": port,
        "url": _url(port),
        "pid_alive": alive,
        "probe": probe,
        "log_file": str(LOG_FILE),
        "server_script": str(SERVER_SCRIPT),
    }


@mcp.tool()
def image_edit_status() -> str:
    """Report whether the local paint-to-edit canvas is running (127.0.0.1 only)."""
    return json.dumps(status_payload(), ensure_ascii=False, indent=2)


@mcp.tool()
def image_edit_ensure(port: int = 0) -> str:
    """Start the local canvas server if it is not already up. Does not open a browser."""
    p = int(port) if port else _port()
    st = status_payload()
    if st["running"] and st["port"] == p:
        return json.dumps({"ok": True, "already": True, **st}, ensure_ascii=False, indent=2)
    if st["running"] and st["port"] != p:
        return json.dumps(
            {
                "ok": True,
                "already": True,
                "note": "服务已在另一个端口运行，没有重复启动。",
                **st,
            },
            ensure_ascii=False,
            indent=2,
        )
    try:
        sock = socket.socket()
        sock.bind(("127.0.0.1", p))
        sock.close()
    except OSError:
        probe = _probe(p)
        if probe.get("ok"):
            return json.dumps({"ok": True, "already": True, "port": p, "url": _url(p), "probe": probe}, ensure_ascii=False, indent=2)
        return json.dumps({"ok": False, "error": "端口 %d 被占用，且探活失败。" % p}, ensure_ascii=False)
    pid = _spawn(p)
    wait = _wait_up(p)
    out = {
        "ok": bool(wait.get("ok")),
        "spawned_pid": pid,
        "port": p,
        "url": _url(p),
        "probe": wait,
        "log_file": str(LOG_FILE),
    }
    if not out["ok"]:
        out["error"] = "服务已拉起但 %ss 内没有应答。看 server.log。" % 25
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool()
def image_edit_open(port: int = 0) -> str:
    """Ensure the local canvas is running, then open it in the default browser. User paints the mask there."""
    raw = image_edit_ensure(port)
    data = json.loads(raw)
    if not data.get("ok"):
        return raw
    url = data.get("url") or _url(port or _port())
    opened = webbrowser.open(url)
    data["opened_browser"] = bool(opened)
    data["instruction"] = (
        "已打开本地改图页。用户必须在画布上亲手涂抹要改的区域，"
        "然后在页面里填 Base URL / API Key / 模型 / 提示词再提交。"
        "不要用模型去猜矩形或自动生成遮罩。"
    )
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def image_edit_stop() -> str:
    """Stop the local canvas server. The next ensure/open will start a new process."""
    st = status_payload()
    pid = st.get("pid")
    stopped = False
    if pid:
        _kill(int(pid))
        stopped = True
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except OSError:
        pass
    time.sleep(0.3)
    after = status_payload()
    return json.dumps({"ok": True, "stopped": stopped, "before": st, "after": after}, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
