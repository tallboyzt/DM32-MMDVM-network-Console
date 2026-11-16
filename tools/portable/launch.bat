@echo off
setlocal
cd /d "%~dp0"

if not exist "runtime\python.exe" (
  echo [ERROR] runtime\python.exe is missing.
  echo Please extract the whole ZIP to a folder and run launch.bat from there.
  pause
  exit /b 1
)

"runtime\python.exe" "tools\launch.py"
if errorlevel 1 pause
