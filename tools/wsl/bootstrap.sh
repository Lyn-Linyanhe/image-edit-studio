#!/usr/bin/env bash
# 一次性引导：在 WSL 侧建立 venv 并安装固定版本依赖。
#
# 用法（Windows 侧，全 ASCII 只有路径）：
#   wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/bootstrap.sh
#
# 幂等：venv 已存在则复用。可用 MANTU_VENV / MANTU_PIP_INDEX 覆盖默认值。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ="$HERE/requirements.txt"
LINUX_HOME="${HOME}"
VENV="${MANTU_VENV:-$LINUX_HOME/.venvs/mantu}"
INDEX="${MANTU_PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"

echo "linux home : $LINUX_HOME"
echo "venv       : $VENV"
echo "index      : $INDEX"
echo "reqs       : $REQ"

if [ ! -x "$VENV/bin/python" ]; then
    echo "→ 创建 venv"
    python3 -m venv "$VENV"
else
    echo "→ venv 已存在，复用"
fi

"$VENV/bin/python" -m pip install --disable-pip-version-check -q -i "$INDEX" --upgrade pip
"$VENV/bin/python" -m pip install --disable-pip-version-check -i "$INDEX" -r "$REQ"

echo "→ 校验导入"
"$VENV/bin/python" - <<'PY'
import PIL
import numpy
import cv2
print("pillow", PIL.__version__)
print("numpy ", numpy.__version__)
print("opencv", cv2.__version__)
PY
echo "bootstrap OK"
