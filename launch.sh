#!/bin/bash
# launch.sh — 启动 MMDVM 控制台 (服务器 + 浏览器)
# 用法: ./launch.sh [--no-open]
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-/usr/local/bin/python3}"
NO_OPEN=""

for a in "$@"; do
  [ "$a" = "--no-open" ] && NO_OPEN=1
done

# 读取端口 (macOS 配置在 Application Support; 否则用 config.json)
CONF="$HOME/Library/Application Support/MMDVM-Console/config.json"
if [ ! -f "$CONF" ]; then
  CONF="$DIR/config.json"
fi
PORT=8080
if [ -f "$CONF" ]; then
  PORT="$("$PYTHON" -c "import json,sys;print(json.load(open(sys.argv[1])).get('web_port',8080))" "$CONF" 2>/dev/null || echo 8080)"
fi

# 若服务器未运行, 启动
if ! curl -s -m 2 "http://localhost:$PORT/api/mode" >/dev/null 2>&1; then
  nohup "$PYTHON" "$DIR/app/server.py" > /tmp/mmdvm-console.log 2>&1 &
  sleep 2
fi

echo "MMDVM 控制台: http://localhost:$PORT/"
[ -z "$NO_OPEN" ] && open "http://localhost:$PORT/"
