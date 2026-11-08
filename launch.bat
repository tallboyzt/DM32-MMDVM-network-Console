@echo off
rem launch.bat — 启动 MMDVM 控制台 (Windows)
setlocal
cd /d "%~dp0"

rem 找 Python
set PY=python
where python >nul 2>&1
if errorlevel 1 set PY=py
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo 错误: 未找到 Python3。请先安装: https://www.python.org/downloads/
  pause
  exit /b 1
)

rem 首次运行: 生成配置 (如无)
if not exist "%APPDATA%\MMDVM-Console" mkdir "%APPDATA%\MMDVM-Console"
if not exist "%APPDATA%\MMDVM-Console\config.json" copy "%~dp0config.example.json" "%APPDATA%\MMDVM-Console\config.json" >nul

set PORT=8080
for /f %%i in ('%PY% -c "import json,os;print(json.load(open(os.path.join(os.environ['APPDATA'],'MMDVM-Console','config.json'))).get('web_port',8080))" 2^>nul') do set PORT=%%i

rem 若服务器未运行则启动
curl -s -m 2 http://localhost:%PORT%/api/mode >nul 2>&1
if errorlevel 1 (
  start "MMDVM控制台" /min %PY% "%~dp0app\server.py"
  timeout /t 2 /nobreak >nul
)

start "" http://localhost:%PORT%/
