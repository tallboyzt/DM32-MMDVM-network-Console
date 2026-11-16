#!/usr/bin/env bash
# 列出 bin/ 下每个 exe/dll 直接导入的 DLL，用来确认运行时依赖齐全
export PATH=/ucrt64/bin:/usr/bin:$PATH
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/bin" || exit 1
for f in *.exe *.dll; do
  echo "== $f"
  objdump -p "$f" 2>/dev/null | grep 'DLL Name' | awk '{print "   " $3}' | sort -u
done
