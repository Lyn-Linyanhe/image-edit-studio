#!/usr/bin/env bash
# Windows+WSL2 搭配实测 · WSL 侧电池（与 bench_win.ps1 对称，同代码同样本）
set -uo pipefail

L=/home/typ/bench                 # Linux 侧工作区
W=/mnt/c/Users/typ/AppData/Local/Temp/mantu_g5   # Windows 侧临时区（跨文件系统）
BIG=/mnt/c/Users/typ/Desktop/mantu/图生图用/Image_1789303749874_925.png
mkdir -p "$L" "$W/small_wsl"

now() { date +%s%N; }
el()  { awk -v a="$1" -v b="$2" 'BEGIN{printf "%.3f", (b-a)/1e9}'; }
best3() { # best3 <函数名> -> 最好一次秒数
    local fn=$1 out="" i t0 t1 s b=""
    for i in 1 2 3; do
        t0=$(now); "$fn"; t1=$(now); s=$(el "$t0" "$t1")
        if [ -z "$b" ] || awk -v x="$s" -v y="$b" 'BEGIN{exit !(x<y)}'; then b=$s; fi
    done
    printf '%s' "$b"
}

echo "== A 环境 =="
. /etc/os-release
echo "distro=$PRETTY_NAME"
echo "kernel=$(uname -r)"
echo "python=$(python3 -V 2>&1)"
echo "cpu=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ //')"
echo "cpu_cores=$(nproc)"
echo "mem_total_mb=$(free -m | awk '/Mem:/{print $2}')"
echo "mem_used_mb=$(free -m | awk '/Mem:/{print $3}')"
echo "disk_avail=$(df -h / | awk 'NR==2{print $4}')"

echo
echo "== B CPU（同一段纯 Python 整数循环 3e6 次，3 次取最好）=="
python3 - <<'PY'
import time
best = None
for _ in range(3):
    t = time.perf_counter()
    n = 0
    for i in range(3_000_000):
        n += (i * i) % 7
    d = time.perf_counter() - t
    best = d if best is None or d < best else best
print(f"cpu_pyloop_best={best:.3f}s")
PY

echo
echo "== C 磁盘：顺序读（同一份 18MB PNG）=="
f_read_big() { sha256sum "$BIG" >/dev/null 2>&1; }
echo "seqread_bigfile_mntc=$(best3 f_read_big)s"

echo "== C 磁盘：顺序写 64MB =="
f_write_native() { dd if=/dev/zero of="$L/big.bin" bs=1M count=64 conv=fsync >/dev/null 2>&1; }
f_write_mntc()   { dd if=/dev/zero of="$W/big_wsl.bin" bs=1M count=64 conv=fsync >/dev/null 2>&1; }
echo "seqwrite_64mb_linuxfs=$(best3 f_write_native)s"
echo "seqwrite_64mb_mntc=$(best3 f_write_mntc)s"

echo "== C 磁盘：500 个 1KB 小文件（创建 / 读取）=="
f_small_native() {
    rm -rf "$L/small"; mkdir -p "$L/small"
    for i in $(seq 1 500); do printf 'x%.0s' $(seq 1 1024) > "$L/small/f$i.txt"; done
}
f_small_read_native() { cat "$L"/small/*.txt > /dev/null 2>&1; }
f_small_mntc() {
    rm -rf "$W/small_wsl"; mkdir -p "$W/small_wsl"
    for i in $(seq 1 500); do printf 'x%.0s' $(seq 1 1024) > "$W/small_wsl/f$i.txt"; done
}
f_small_read_mntc() { cat "$W"/small_wsl/*.txt > /dev/null 2>&1; }
echo "smallfiles_create_500_linuxfs=$(best3 f_small_native)s"
echo "smallfiles_read_500_linuxfs=$(best3 f_small_read_native)s"
echo "smallfiles_create_500_mntc=$(best3 f_small_mntc)s"
echo "smallfiles_read_500_mntc=$(best3 f_small_read_mntc)s"

echo
echo "== D 网络：RTT（5 次取均值）=="
for h in image-direct.geiliapi.com pypi.tuna.tsinghua.edu.cn; do
    r=$(ping -c 5 -W 3 "$h" 2>/dev/null | awk -F'/' '/rtt|round-trip/{print $5}')
    echo "rtt_avg_ms[$h]=${r:-失败}"
done

echo "== D 网络：下载吞吐（清华 pypi 上的 pillow 轮子，固定版本）=="
URL=$(curl -s --max-time 20 https://pypi.tuna.tsinghua.edu.cn/simple/pillow/ \
      | grep -o 'https[^"]*pillow-12\.3\.0-cp312[^"]*manylinux_2_28_x86_64\.whl' | head -1)
if [ -n "$URL" ]; then
    b=""
    for i in 1 2 3; do
        t0=$(now); curl -s -o /dev/null --max-time 60 "$URL"; t1=$(now); s=$(el "$t0" "$t1")
        if [ -z "$b" ] || awk -v x="$s" -v y="$b" 'BEGIN{exit !(x<y)}'; then b=$s; fi
    done
    echo "download_6.9MB_best=${b}s"
    awk -v s="$b" 'BEGIN{printf "download_MBps=%.1f\n", 6.9/s}'
else
    echo "download=跳过（未解析到 URL）"
fi

echo
echo "== E GPU =="
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | sed 's/^/gpu=/'
    [ -e /dev/dxg ] && echo "dev_dxg=存在" || echo "dev_dxg=缺失"
else
    echo "gpu=nvidia-smi 不可用"
fi

echo
echo "== F GUI / X =="
echo "DISPLAY=${DISPLAY:-未设置}"
ls /tmp/.X11-unix/ 2>/dev/null | sed 's/^/x11_socket=/' || echo "x11_socket=无"
for c in xdpyinfo xeyes xmessage; do
    command -v $c >/dev/null 2>&1 && echo "xclient_$c=有" || echo "xclient_$c=无"
done
python3 -c "import tkinter; print('tkinter=有')" 2>/dev/null || echo "tkinter=无"

echo
echo "== G 跨边界编码往返 =="
printf '中文哨兵：文件台账 ①②③ — ZWSP测试\n' > "$W/enc_wsl2win.txt"
echo "wsl_wrote=$W/enc_wsl2win.txt"
if [ -r "$W/enc_win2wsl.txt" ]; then
    echo "read_from_windows=$(head -1 "$W/enc_win2wsl.txt")"
else
    echo "read_from_windows=（Windows 侧文件尚未生成）"
fi
echo "DONE_WSL"
