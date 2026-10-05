#!/usr/bin/env bash
# WSL 通道机械门禁：验证通道环境是否满足开工条件。任一 FAIL → 退出码 1。
#
# 用法（Windows 侧，全 ASCII 只有路径）：
#   $env:WSL_UTF8='1'
#   wsl.exe -d Ubuntu-24.04 -e bash .../tools/wsl/doctor.sh
#   wsl.exe -d Ubuntu-24.04 -e bash .../tools/wsl/doctor.sh --io <产物目录>    # 追加 G5 计时
#
# 门禁定义、阈值与不通过时的处置，见 docs/环境_Windows与WSL2混用.md。
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN="$HERE/wslrun.sh"
PROBE="$HERE/probe_env.py"
LINUX_HOME="$HOME"
WIN_HOME="${MANTU_WIN_HOME:-/mnt/c/Users/<用户名>}"
VENV="${MANTU_VENV:-$LINUX_HOME/.venvs/mantu}"
SKILL_AUDIT="$WIN_HOME/.agents/skills/style-distill/scripts/audit_and_check.py"
IO_DIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --io) IO_DIR="${2:-}"; shift 2 ;;
        --repeat) REPEAT="${2:-1}"; shift 2 ;;
        -h|--help) sed -n '3,10p' "$0"; exit 0 ;;
        *) echo "doctor: 未知参数 $1" >&2; exit 2 ;;
    esac
done
REPEAT="${REPEAT:-1}"

PASS=0; FAIL=0; WARN=0
ok()   { printf '  [PASS] %s\n           %s\n' "$1" "$2"; PASS=$((PASS + 1)); }
bad()  { printf '  [FAIL] %s\n           %s\n' "$1" "$2"; FAIL=$((FAIL + 1)); }
warn() { printf '  [WARN] %s\n           %s\n' "$1" "$2"; WARN=$((WARN + 1)); }
info() { printf '  [info] %s\n' "$1"; }

echo "=============================================================="
echo "WSL 通道门禁 · G2–G6"
echo "=============================================================="
info "distro    : $(. /etc/os-release; echo "$PRETTY_NAME")"
info "kernel    : $(uname -r)"
info "linux home: $LINUX_HOME"
info "win home  : $WIN_HOME"
info "venv      : $VENV"

ERRLOG="${TMPDIR:-/tmp}/mantu_probe.err"
if [ ! -x "$VENV/bin/python" ]; then
    bad "前置 venv" "$VENV/bin/python 不存在 → 先跑 tools/wsl/bootstrap.sh"
fi
# 探针只跑两次（带凭据 / 刻意不带凭据），后续字段都从这里取：
# 既避免每字段起一次子进程，也避免把失败原因 2>/dev/null 吞掉（第一版就是这么瞎的）。
PROBE_OUT=$(bash "$RUN" -- "$VENV/bin/python" "$PROBE" --plain 2>"$ERRLOG")
PROBE_NO=$(env MANTU_CRED_FILE=/nonexistent bash "$RUN" -- "$VENV/bin/python" "$PROBE" --plain 2>/dev/null)
field() { printf '%s\n' "$1" | awk -F= -v k="$2" '$1==k{print $2; exit}'; }
probe_evidence() {
    if [ -n "$PROBE_OUT" ]; then printf ''; else
        printf '探针无输出；stderr: %s' "$(tail -n 2 "$ERRLOG" | tr '\n' ' ')"
    fi
}

# ---------- G2 编码 ----------
echo
map=$(locale charmap 2>/dev/null || echo "?")
if [ "$map" = "UTF-8" ]; then
    ok "G2a 语言环境为 UTF-8" "locale charmap=$map（调用侧还须设 WSL_UTF8=1，否则 wsl.exe 输出在 pwsh 里是 UTF-16 乱码）"
else
    bad "G2a 语言环境为 UTF-8" "locale charmap=$map"
fi
echo "  [哨兵] 中文哨兵：汉字 ①②③，全角标点「。」——若你在上面这行看到乱码，请检查 WSL_UTF8=1"

# ---------- G3 凭据 ----------
echo
if [ ! -r "$LINUX_HOME/.config/mantu/relay.env" ]; then
    warn "G3 凭据通道" "凭据文件不存在或不可读：$LINUX_HOME/.config/mantu/relay.env → 通道仅限不需要出图的任务"
else
    imp=$(field "$PROBE_OUT" import_ok)
    key=$(field "$PROBE_OUT" relay_key)
    if [ "$imp" = "true" ] && [ "$key" = "true" ]; then
        ok "G3 凭据可用（真实代码路径）" "mask_edit_app.env_cred('RELAY_API_KEY') 非空；import_ok=$imp"
    else
        bad "G3 凭据可用" "import_ok=$imp relay_key=$key $(probe_evidence) —— 未通过则 WSL 一律不承接出图任务"
    fi
    before=$(field "$PROBE_NO" relay_key)
    info "对照：跳过注入时 relay_key=${before:-（无输出）}（预期 false，说明这门禁确有区分度）"
fi

# ---------- G4 HOME 对齐 ----------
echo
p_home=$(field "$PROBE_OUT" home)
p_skill=$(field "$PROBE_OUT" skill_audit_exists)
p_att=$(field "$PROBE_OUT" dsh_attachments_exists)
p_sess=$(field "$PROBE_OUT" session_dir_exists)
if [ "$p_skill" = "true" ] && [ "$p_att" = "true" ]; then
    ok "G4 HOME 对齐" "home=$p_home；skill_audit_exists=$p_skill；dsh_attachments_exists=$p_att；session_dir_exists=$p_sess"
else
    bad "G4 HOME 对齐" "home=$p_home；skill_audit_exists=$p_skill；dsh_attachments_exists=$p_att $(probe_evidence) → 不得在 WSL 跑 run_round.py"
fi
if [ -e "$LINUX_HOME/.agents/skills/style-distill/scripts/audit_and_check.py" ]; then
    info "未对齐的 Linux 家目录下也存在同名路径 → 对齐的正反区分不成立，须单独复核"
else
    info "对照：未对齐时 $LINUX_HOME/.agents/… 不存在（预期）——run_round.py:537 会因此静默跳过体检"
fi

# ---------- G5 计时（可选） ----------
echo
if [ -n "$IO_DIR" ]; then
    if [ ! -d "$IO_DIR" ]; then
        bad "G5 I/O 计时" "目录不存在：$IO_DIR"
    else
        n=$(find "$IO_DIR" -maxdepth 2 -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) | wc -l)
        sz=$(du -sh "$IO_DIR" 2>/dev/null | cut -f1)
        list=""; best=""; rc_all=0; i=1
        while [ "$i" -le "$REPEAT" ]; do
            t0=$(date +%s%N)
            "$RUN" "$SKILL_AUDIT" audit "$IO_DIR" >/dev/null 2>&1
            rc=$?
            t1=$(date +%s%N)
            s=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f", (b-a)/1e9}')
            [ "$rc" -eq 0 ] || rc_all=$rc
            list="$list $s"
            if [ -z "$best" ] || awk -v x="$s" -v y="$best" 'BEGIN{exit !(x < y)}'; then best="$s"; fi
            i=$((i + 1))
        done
        if [ "$rc_all" -eq 0 ]; then
            ok "G5 I/O 计时（每次 = 一次 complete audit，含进程启动）" \
               "样本 ${n} 张 / ${sz}；共 ${REPEAT} 次:${list}；最好 ${best}s"
        else
            bad "G5 I/O 计时" "audit 退出码 $rc_all；样本 ${n} 张 / ${sz}"
        fi
        info "同批样本还需在 Windows 侧（C:\\Python314）与 Linux 原生副本各测一次，按 t_wsl ≤ 1.5×t_w 判定适用范围"
    fi
else
    info "G5 未跑（加 --io <产物目录> 可计时）"
fi

# ---------- G6 行尾与语法 ----------
echo
lf_bad=""; syn_bad=""; cnt=0
for f in "$HERE"/*.sh; do
    [ -f "$f" ] || continue
    cnt=$((cnt + 1))
    c=$(LC_ALL=C grep -ac $'\r' "$f" 2>/dev/null || true)
    [ "${c:-0}" = "0" ] || lf_bad="$lf_bad $(basename "$f")"
    bash -n "$f" 2>/dev/null || syn_bad="$syn_bad $(basename "$f")"
done
if [ -z "$lf_bad" ] && [ -z "$syn_bad" ]; then
    ok "G6 新增 .sh 为 LF 且语法通过" "扫过 $cnt 个 .sh，均无 0x0D；bash -n 全通过"
else
    bad "G6 .sh 行尾/语法" "含 CR:${lf_bad:- 无}；语法错:${syn_bad:- 无}"
fi

# ---------- 附加：陷阱与非门禁信息 ----------
echo
if command -v node >/dev/null 2>&1; then
    info "node: $(command -v node) —— 存在真实 Linux node，可用于 Linux 侧工具（但 DSH 仍不搬）"
else
    shims=""
    for c in npm npx pnpm; do
        p=$(command -v "$c" 2>/dev/null || true)
        case "$p" in /mnt/*) shims="$shims $c→$p" ;; esac
    done
    if [ -n "$shims" ]; then
        warn "node 陷阱" "node 不存在，但发现 Windows 侧 shim 漏进 PATH：$shims —— 这些会失败；也禁止从 WSL 调 node.exe（那是 Windows 进程）"
    else
        info "node 不存在，且未发现 /mnt 下的 npm/npx/pnpm shim"
    fi
fi
echo "  [info] 网络：中转站直连可用；Windows 本地代理 127.0.0.1:7890 在 WSL 不可达（需代理的下载不要在 WSL 做）"
if command -v curl >/dev/null 2>&1; then
    out=$(curl -s -o /dev/null -w '%{http_code} %{time_total}' --max-time 20 https://image-direct.geiliapi.com/ 2>/dev/null || true)
    info "中转站直连探测：http=${out:-失败}（该站 / 路径返回 404＝可达；首次连接可能需 5s 以上，故超时给到 20s）"
fi

echo
echo "=============================================================="
echo "门禁汇总：PASS=$PASS  FAIL=$FAIL  WARN=$WARN"
echo "=============================================================="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
