#!/usr/bin/env bash
# WSL → Windows 可达性探测：Windows 上跑着一个监听 0.0.0.0:8124 的服务
set -uo pipefail
HOSTIP="${1:-172.18.64.1}"
echo "目标：Windows 上的 http.server 8124（监听 0.0.0.0）"
for t in "$HOSTIP" 127.0.0.1; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "http://$t:8124/" 2>/dev/null)
    rc=$?
    if [ "$rc" -eq 0 ] && [ "$code" = "200" ]; then
        echo "  http://$t:8124/ -> 200 可达"
    else
        echo "  http://$t:8124/ -> 不可达 (curl_rc=$rc, http=$code)"
    fi
done
echo "默认网关（=Windows 宿主）: $(ip -4 route | awk '/^default/{print $3; exit}')"
