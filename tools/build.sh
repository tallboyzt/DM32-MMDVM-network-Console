#!/usr/bin/env bash
# 用 MSYS2 UCRT64 工具链编译 MMDVM-Host / DMRGateway，产物放到 bin/
# 依赖: tools/msys2-setup.sh 装好的 mingw-w64-ucrt-x86_64-{gcc,mosquitto,nlohmann-json}
# 源码: src/MMDVM-Host, src/DMRGateway (g4klx)
set -euo pipefail

export PATH=/ucrt64/bin:/usr/bin:$PATH
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/bin"
mkdir -p "$BIN"

test -d "$ROOT/src/MMDVM-Host" || { echo "缺少 src/MMDVM-Host：git clone https://github.com/g4klx/MMDVM-Host.git src/MMDVM-Host"; exit 1; }
test -d "$ROOT/src/DMRGateway" || { echo "缺少 src/DMRGateway：git clone https://github.com/g4klx/DMRGateway.git src/DMRGateway"; exit 1; }

echo "== gcc: $(gcc --version | head -1)"

echo "== build MMDVM-Host"
cd "$ROOT/src/MMDVM-Host"
make clean >/dev/null 2>&1 || true
make -j"$(nproc)" LIBS="-lpthread -lmosquitto -lws2_32" \
  CFLAGS="-O2 -Wall -std=c++17 -Wno-psabi -pthread"

echo "== build DMRGateway"
cd "$ROOT/src/DMRGateway"
make clean >/dev/null 2>&1 || true
make -j"$(nproc)" LIBS="-lpthread -lmosquitto -lws2_32" \
  CFLAGS="-O2 -Wall -std=c++0x -pthread"

cp -f "$ROOT/src/MMDVM-Host/MMDVM-Host.exe" "$BIN/MMDVMHost.exe"
cp -f "$ROOT/src/DMRGateway/DMRGateway.exe" "$BIN/DMRGateway.exe"

echo "== copy runtime DLLs"
for exe in "$BIN/MMDVMHost.exe" "$BIN/DMRGateway.exe"; do
  ldd "$exe" | awk '{print $3}' | grep '^/ucrt64' | while read -r dll; do
    cp -f "$dll" "$BIN/" || true
  done
done

echo "== done"
ls -l "$BIN"
