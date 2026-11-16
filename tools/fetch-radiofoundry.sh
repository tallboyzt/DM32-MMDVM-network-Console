#!/usr/bin/env bash
# 获取 RadioFoundry 的 tools/ 与 stub/（调试链路，Windows 电台面板和便携包要用）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DST="$ROOT/tools/radiofoundry"
if [ -d "$DST/tools" ] && [ -d "$DST/stub" ]; then
  echo "already present: $DST"
  exit 0
fi
git clone --depth 1 --filter=blob:none --sparse https://github.com/RadioFoundry/RadioFoundry.git "$DST"
git -C "$DST" sparse-checkout set tools stub
echo "ok: $DST"
