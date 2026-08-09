#!/bin/bash
set -e

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# 从 config/.env 读取 SEARCH_API_PORT，未找到则默认 8088
PORT=$(grep -E '^SEARCH_API_PORT=' config/.env | cut -d= -f2 | tail -n1)
PORT=${PORT:-8088}

# 启动服务（后台）
echo "启动文献可视化服务，端口 ${PORT} ..."
python code/search/api.py --port "$PORT" &
PID=$!

# 等待服务启动
sleep 2

# 尝试打开浏览器
URL="http://localhost:${PORT}/"
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" || true
elif command -v open >/dev/null 2>&1; then
    open "$URL" || true
else
    echo "请手动打开浏览器访问: $URL"
fi

# 等待服务进程结束
wait "$PID"
