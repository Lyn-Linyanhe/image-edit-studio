#!/usr/bin/env bash
# 单次下载计时（供 dl_dist.ps1 调用）：打印耗时秒数
# 用法： dl_once.sh [额外的 curl 参数]   例： dl_once.sh --http1.1
set -uo pipefail

URL='https://pypi.tuna.tsinghua.edu.cn/packages/84/21/a35af28dcc61f37ed850a2d64c65c701321dfbf25085e469d5559360cbbf/pillow-12.3.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl'
EXTRA="${1:-}"

t0=$(date +%s%N)
# shellcheck disable=SC2086
curl -s $EXTRA -o /dev/null --max-time 120 "$URL"
rc=$?
t1=$(date +%s%N)

if [ "$rc" -ne 0 ]; then
    echo "curl_rc=$rc" >&2
fi
awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f\n", (b-a)/1e9}'
