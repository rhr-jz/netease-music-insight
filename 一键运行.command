#!/bin/bash

cd -- "$(dirname -- "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

finish() {
  status=$1
  echo
  read -r -p "按 Return 键关闭窗口……" _
  exit "$status"
}

python_cmd=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && \
     "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    python_cmd=$candidate
    break
  fi
done

if [ -z "$python_cmd" ]; then
  echo "未找到 Python 3.10 或更新版本。"
  echo "请从 https://www.python.org/downloads/macos/ 安装后重试。"
  finish 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/2] 首次运行：创建独立运行环境……"
  "$python_cmd" -m venv .venv || {
    echo "创建 Python 运行环境失败。"
    finish 1
  }
fi

if ! .venv/bin/python -c "import requests, qrcode, PIL, qqmusic_api" >/dev/null 2>&1; then
  echo "[2/2] 安装 Python 依赖……"
  .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt || {
    echo "安装失败。请检查网络、磁盘空间和文件夹写入权限后重试。"
    finish 1
  }
fi

.venv/bin/python run.py "$@"
exit_code=$?
finish "$exit_code"
