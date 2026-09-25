#!/usr/bin/env bash
# 下载吞吐对照（同一绝对 URL，两侧同脚本语义）
set -uo pipefail
URL='https://pypi.tuna.tsinghua.edu.cn/packages/84/21/a35af28dcc61f37ed850a2d64c65c701321dfbf25085e469d5559360cbbf/pillow-12.3.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl'
SIZE=6.9
best=""
for i in 1 2 3; do
    t0=$(date +%s%N)
    curl -s -o /dev/null --max-time 90 "$URL"
    rc=$?
    t1=$(date +%s%N)
    s=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f", (b-a)/1e9}')
    echo "  run$i=${s}s (curl_rc=$rc)"
    if [ -z "$best" ] || awk -v x="$s" -v y="$best" 'BEGIN{exit !(x<y)}'; then best=$s; fi
done
echo "download_best=${best}s"
awk -v s="$best" -v m="$SIZE" 'BEGIN{printf "download_MBps=%.1f\n", m/s}'
