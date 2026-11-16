#!/usr/bin/env bash
# 一步到位安装 MSYS2 UCRT64 工具链（国内走 TUNA 镜像），用于编译 MMDVMHost / DMRGateway
# 用法（在已经装好 MSYS2 的前提下）: C:\msys64\usr\bin\bash.exe -lc "tools/msys2-setup.sh"
set -uo pipefail

for f in /etc/pacman.d/mirrorlist.*; do
  sed -i 's|https://mirror.msys2.org|https://mirrors.tuna.tsinghua.edu.cn/msys2|g' "$f" 2>/dev/null || true
done

pacman-key --init 2>/dev/null || true
pacman-key --populate msys2 2>/dev/null || true

pacman -Syuu --noconfirm
pacman -Suu --noconfirm || true

pacman -S --noconfirm --needed \
  make git \
  mingw-w64-ucrt-x86_64-gcc \
  mingw-w64-ucrt-x86_64-mosquitto \
  mingw-w64-ucrt-x86_64-nlohmann-json

echo "SETUP-DONE"
