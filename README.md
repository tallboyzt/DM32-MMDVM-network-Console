# MMDVM 控制台 (通用版)

一个**通用**的 MMDVM 热点控制台：管理 MMDVMHost / DMRGateway，一键在「热点模式」和「电台网络模式」间切换，跨平台（macOS / Windows），独立 App，密码只需输入一次。

> 由 [RadioFoundry](https://github.com/RadioFoundry/RadioFoundry) 生态的 DM-32UV 电台使用场景整理而来。

---

## 功能

- **热点模式**：启动 / 停止 / 重启 MMDVMHost + DMRGateway，查看状态（呼号、频率、DMR ID）、最近通联（QSO）、日志。
- **参数设置**：直接改 MMDVMHost / DMRGateway 常用参数（呼号、DMR ID、接收/发射频率、色码、时隙、网络服务器/端口/密码），保存后重启生效。
- **网络模式**：一键切到**电台控制面板**（实时信道、频率、电量等）。macOS 走串口 PPP 内嵌电台网页；Windows 用 RadioFoundry 调试链路直接读屏 + 按键（DM-32UV 无原生 USB，见下文）。
- **密码一次**：macOS 切换网络模式需要管理员密码，**只需输入一次**，存在本机钥匙串（Keychain），不再反复输入。
- **通用配置**：`config.json` 配置（路径、DMR ID、呼号、频率、串口），不写死任何设备；路径支持相对值，整包复制到别的电脑不用改。
- **跨平台**：macOS `.app` + Windows 启动器（`launch.bat`）+ **Windows 免安装便携版**。
- **便携版**：`tools/make_portable.ps1` 一条命令打包成内置 Python 的 zip，解压双击即用。

---

## 要求

| 平台 | 依赖 |
|------|------|
| macOS | Python 3（`/usr/local/bin/python3` 或 `python3`）；MMDVMHost / DMRGateway 二进制 |
| Windows | Python 3（[python.org](https://www.python.org/downloads/)）；MMDVMHost.exe / DMRGateway.exe（可用 `tools/build.sh` 自行编译）；网络模式另需 `pyserial` 与 `tools/radiofoundry/` |

> MMDVMHost / DMRGateway 官方只发布源码：从 [g4klx/MMDVM-Host](https://github.com/g4klx/MMDVM-Host)（含 [W0CHP 改进版](https://github.com/W0CHP/MMDVMHost)）获取，放到任意目录，在配置里填路径即可；Windows 下的编译方法见下文。

---

## 安装

### macOS（独立 App）

```bash
chmod +x make_app.sh launch.sh app/ppp_start.sh
./make_app.sh           # 默认生成到 /Applications，生成 "MMDVM控制台.app"
open /Applications/MMDVM控制台.app
```

> 首次运行请先配置（见下）。

### Windows

```bat
:: 双击 launch.bat，或：
launch.bat
```

首次运行会在 `%APPDATA%\MMDVM-Console\config.json` 生成配置模板，请编辑后重开。

MMDVMHost / DMRGateway 在 Windows 上需要自己编译（MSYS2 UCRT64 工具链）：

```bash
# 1. 在 MSYS2 的 UCRT64 shell 里装编译环境
tools/msys2-setup.sh
# 2. 取源码（放 src/ 下）
git clone https://github.com/g4klx/MMDVM-Host.git src/MMDVM-Host
git clone https://github.com/g4klx/DMRGateway.git src/DMRGateway
# 3. 编译，可执行文件与运行库进 bin/
tools/build.sh
```

`mmdvm/` 下是热点配置模板（`MMDVM.ini`、`DMRGateway.ini`），可用 `python tools/make_ini.py` 按默认值重新生成。
控制台与 MMDVMHost 之间用本机 `127.0.0.1:62031/62032` 的 MMDVM 协议对接。

### Windows 便携版（免安装，推荐发给别人）

```text
powershell -ExecutionPolicy Bypass -File tools\make_portable.ps1
```

生成 `MMDVM-Console-Portable-win64.zip`（约 16 MB）：内置 Python 3.13 与 pyserial、`bin/` 里的可执行文件和
运行库、`mmdvm/` 配置、调试链路，以及启动器。目标机解压后双击 `launch.bat` 即可，**不需要装 Python、不需要编译**。

首次启动会自动：
- 在包内生成 `config.json`（路径全是相对值，整个文件夹搬走也不失效）；
- 把 `mmdvm/MMDVM.ini` 里的 `UARTPort` 换成这台电脑上实际存在的串口。

---

## 配置

配置文件位置：

- macOS：`~/Library/Application Support/MMDVM-Console/config.json`
- Windows：`%APPDATA%\MMDVM-Console\config.json`
- 便携版：包内 `config.json`（用 `--config` 指定）

参照 `config.example.json`：

```json
{
  "serial_port": "",                 // 串口，留空自动检测 (macOS: /dev/cu.usbserial-*, Windows: COM*)
  "mmdvm_host_path": "bin/MMDVMHost.exe",
  "dmrgateway_path": "bin/DMRGateway.exe",
  "mmdvm_ini_path": "mmdvm/MMDVM.ini",
  "dmrgateway_ini_path": "mmdvm/DMRGateway.ini",
  "dmr_id": "4600001",               // 你的 DMR ID
  "callsign": "BG0ABC",
  "frequency_mhz": "438.800",
  "radio_ip": "",                    // 电台网络模式 IP，留空自动由 DMR ID 算出 (12.<ID>)
  "brandmeister": { "server": "4602.master.brandmeister.network", "port": 62031 },
  "web_port": 8080
}
```

> 路径写相对值时按程序根目录解析，所以整包复制到别的电脑不用改。
> `radio_ip` 留空时自动计算：主机 `12.<DMR ID>`，电台为末字节 ^1（如 DMR ID 8600309 → 主机 `12.131.58.245`、电台 `12.131.58.244`）。

---

## 使用

1. 打开控制台（双击 App / `launch.bat`），浏览器自动打开 `http://localhost:8080/`。
2. 首次切换网络模式，macOS 会提示**输入管理员密码**（输入一次即可，存钥匙串）。
3. 点 **「切换到网络」** → 界面变为电台控制面板；点 **「切换回热点」** 返回。
4. 热点模式下可 启动 / 停止 / 重启 链路，看状态、通联、日志。

### 网络模式说明

- **macOS**：经串口线建立 PPP，电台 IP 由 DMR ID 决定；需要管理员权限（密码存钥匙串，只输一次）；链路掉线自动重连（`persist`）。
- **Windows**：DM-32UV 没有原生 USB，网络只能走编程线 PPP，而 Windows 没有 `pppd`。
  控制台改用 RadioFoundry 调试链路（同一条串口线）：约 1 秒刷新一次真实屏幕，按键直接下发到电台，
  不需要驱动、不需要管理员权限。
  依赖 `tools/radiofoundry/`（`tools/fetch-radiofoundry.sh` 获取，便携版已内置）。
  如果你确实需要真正的 IP 网络（`12.x.y.z`、TFTP、KISS、rigctl），Windows 上需要 RAS 拨号 + 虚拟调制解调器，
  或 WSL2 + usbipd 跑 `pppd`，都属于系统级改动。

---

## 目录结构

```
MMDVM-Console/
├── app/
│   ├── server.py        # 跨平台后端 (配置驱动, 密码一次, Windows 电台面板)
│   ├── index.html       # 前端控制台
│   └── ppp_start.sh     # macOS PPP 启动/停止 (nodetach+persist)
├── mmdvm/               # MMDVM.ini / DMRGateway.ini 热点配置
├── tools/
│   ├── msys2-setup.sh   # 安装 MSYS2 UCRT64 编译环境
│   ├── build.sh         # 编译 MMDVMHost / DMRGateway 到 bin/
│   ├── checkdeps.sh     # 检查 bin/ 的 DLL 依赖
│   ├── make_ini.py      # 生成 mmdvm/*.ini
│   ├── fetch-radiofoundry.sh   # 取调试链路（Windows 电台面板/便携包）
│   ├── make_portable.ps1       # 打包 Windows 便携版
│   └── portable/               # 便携版启动器与使用说明
├── config.example.json  # 配置模板
├── launch.sh            # macOS 启动器
├── make_app.sh          # macOS 生成独立 .app
├── launch.bat           # Windows 启动器
└── README.md
```

---

## 安全

- macOS 管理员密码仅存本机钥匙串（Keychain），不上传、不写入配置文件。
- 控制台只监听 `127.0.0.1`（本机），不对外网开放。

## 许可

MIT
