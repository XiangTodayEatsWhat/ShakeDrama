#!/usr/bin/env bash
set -e

# 在项目根目录执行：bash run_local.sh 或 ./run_local.sh
cd "$(dirname "$0")" || exit 1

# 加载项目根目录下的 .env
if [ -f ".env" ]; then
  set -a
  # shellcheck source=/dev/null
  . ".env"
  set +a
  echo "已加载 $(pwd)/.env"
fi

PYTHON_BIN="/home/admin/miniconda3/envs/drama/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python3"
fi

PORT="${AXIS_API_PORT:-8502}"
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "项目目录: $(pwd)"
echo "专业级标准化格式剧本生成"
echo "Python 环境: $PYTHON_BIN"
echo "本机访问: http://localhost:${PORT}"
echo "其他电脑访问: http://${IP:-本机IP}:${PORT}（同一网络下）"
echo ""

"$PYTHON_BIN" app.py
