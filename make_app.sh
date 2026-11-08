#!/bin/bash
# make_app.sh — 生成 macOS 独立 App "MMDVM控制台.app"
# 用法: ./make_app.sh [输出目录]   (默认 /Applications)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-/Applications}"
APP_NAME="MMDVM控制台.app"
EXE="MMDVM控制台"
APP="$OUT/$APP_NAME"

echo "生成: $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/app"

# 拷贝 app 文件 (服务器 + 前端 + PPP 脚本)
cp "$DIR/app/server.py" "$DIR/app/index.html" "$DIR/app/ppp_start.sh" "$APP/Contents/Resources/app/"
chmod +x "$APP/Contents/Resources/app/ppp_start.sh"

# 主执行脚本
cat > "$APP/Contents/MacOS/$EXE" <<'EOF'
#!/bin/bash
APP="$(cd "$(dirname "$0")/.." && pwd)"
RES="$APP/Resources/app"
PYTHON="${PYTHON:-/usr/local/bin/python3}"
CONF="$HOME/Library/Application Support/MMDVM-Console/config.json"
PORT=8080
if [ -f "$CONF" ]; then
  PORT="$("$PYTHON" -c "import json,sys;print(json.load(open(sys.argv[1])).get('web_port',8080))" "$CONF" 2>/dev/null || echo 8080)"
fi
if ! curl -s -m 2 "http://localhost:$PORT/api/mode" >/dev/null 2>&1; then
  nohup "$PYTHON" "$RES/server.py" > /tmp/mmdvm-console.log 2>&1 &
  sleep 2
fi
open "http://localhost:$PORT/"
EOF
chmod +x "$APP/Contents/MacOS/$EXE"

# Info.plist
cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>MMDVM控制台</string>
  <key>CFBundleDisplayName</key><string>MMDVM控制台</string>
  <key>CFBundleIdentifier</key><string>com.tallboy.mmdvm-console</string>
  <key>CFBundleVersion</key><string>1.0.0</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundleExecutable</key><string>MMDVM控制台</string>  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>10.13</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

echo "完成: $APP"
echo "双击即可启动 (首次运行请先配置: 编辑 ~/Library/Application Support/MMDVM-Console/config.json)"
