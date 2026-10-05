#!/usr/bin/env bash
# WSL 通道唯一入口：Windows 仍是主环境，这里只用 WSL 侧的 venv 跑无状态脚本。
#
# 用法（Windows 侧，全 ASCII、只有路径——这是本通道存在的意义）：
#   $env:WSL_UTF8='1'
#   wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/<用户名>/Desktop/mantu/tools/wsl/wslrun.sh <脚本路径> [参数…]
#   wsl.exe -d Ubuntu-24.04 -e bash .../wslrun.sh -- <命令> [参数…]     # 管道/文本工具逃生口
#
# 两件事必须做对（都是实测得来，见 docs/环境_Windows与WSL2混用.md）：
#   1) HOME 必须对齐到 Windows 家目录。否则 Path.home() 系路径全部指错，而且
#      run_round.py:537 用的是 `if check_target and CHECK.exists():` —— 会**静默跳过体检**，
#      不报错、不告警，最难发现。
#   2) 凭据必须显式注入。RELAY_API_KEY 只在 Windows 用户级，WSL 不继承（WSLENV 为空），
#      而 mask_edit_app.env_cred() 在非 Windows 上按设计安静返回默认值。
set -euo pipefail

LINUX_HOME="${HOME}"                                   # 先记下 Linux 家目录：缓存必须留在这边
WIN_HOME="${MANTU_WIN_HOME:-/mnt/c/Users/<用户名>}"
VENV="${MANTU_VENV:-$LINUX_HOME/.venvs/mantu}"
CRED="${MANTU_CRED_FILE:-$LINUX_HOME/.config/mantu/relay.env}"

if [ ! -d "$WIN_HOME" ]; then
    echo "wslrun: Windows 家目录不存在：$WIN_HOME（用 MANTU_WIN_HOME 指定）" >&2
    exit 2
fi
if [ ! -x "$VENV/bin/python" ]; then
    echo "wslrun: venv 不可用：$VENV —— 先跑 tools/wsl/bootstrap.sh" >&2
    exit 2
fi

if [ -r "$CRED" ]; then
    # 用进程替换 + 去 CR 后再 source：Windows 侧任何工具写出来的文件都可能是 CRLF，
    # 而 CRLF 的 `. file` 会报 `$'\r': command not found`，在 set -e 下**整个脚本 127 退出**
    # （这个坑在通道建立当天就实测踩到过一次：PowerShell 管道给末行加了 CRLF）。
    # shellcheck disable=SC1090
    if ! . <(tr -d '\r' < "$CRED"); then
        echo "wslrun: 凭据文件解析失败（语法错？）：$CRED" >&2
    fi
    # `. file` 只设 shell 变量，**不会**自动导出给子进程：不显式 export 的话，
    # 本脚本里 `[ -n "$RELAY_API_KEY" ]` 为真、而 python 的 os.environ 里却是空的
    # （本通道调试期实测踩到的第二个坑，症状是"看着已注入、actual 却是 false"）。
    export RELAY_API_KEY RELAY_API_KEY_HD RELAY_BASE_URL
else
    echo "wslrun: 凭据文件不可读：$CRED（需要出图的脚本会因此报缺 key，这是有意为之）" >&2
fi

export HOME="$WIN_HOME"                                # ← 关键：让 Path.home() 指向 Windows 家目录
export XDG_CACHE_HOME="$LINUX_HOME/.cache"             # 缓存别写进 /mnt/c（9p 慢）
export PIP_CACHE_DIR="$LINUX_HOME/.cache/pip"
export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"
# 故意不设 PYTHONIOENCODING：仓库纪律要求脚本自带 UTF-8 前置（acceptance.py:170 的 B8）

echo "wslrun: HOME=$HOME  venv=$VENV  RELAY_API_KEY=$([ -n "${RELAY_API_KEY:-}" ] && echo 已注入 || echo 未注入)" >&2

if [ "${1:-}" = "--" ]; then
    shift
    if [ $# -lt 1 ]; then
        echo "wslrun: -- 后面要跟命令" >&2
        exit 2
    fi
    echo "wslrun: exec $*" >&2
    exec "$@"
fi

if [ $# -lt 1 ]; then
    echo "wslrun: 用法 wslrun.sh <脚本路径> [参数…] | wslrun.sh -- <命令> [参数…]" >&2
    exit 2
fi

SCRIPT="$1"
shift
if [ ! -f "$SCRIPT" ]; then
    echo "wslrun: 脚本不存在：$SCRIPT" >&2
    exit 2
fi
echo "wslrun: exec $SCRIPT $*" >&2
exec "$VENV/bin/python" "$SCRIPT" "$@"
