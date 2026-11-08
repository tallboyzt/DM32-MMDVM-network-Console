# MMDVM 控制台 (通用版)

一个**通用**的 MMDVM 热点控制台：管理 MMDVMHost / DMRGateway，一键在「热点模式」和「电台网络模式」间切换，跨平台（macOS / Windows），独立 App，密码只需输入一次。

> 由 [RadioFoundry](https://github.com/RadioFoundry/RadioFoundry) 生态的 DM-32UV 电台使用场景整理而来。

---

## 功能

- **热点模式**：启动 / 停止 / 重启 MMDVMHost + DMRGateway，查看状态（呼号、频率、DMR ID）、最近通联（QSO）、日志。
- **参数设置**：直接改 MMDVMHost / DMRGateway 常用参数（呼号、DMR ID、接收/发射频率、色码、时隙、网络服务器/端口/密码），保存后重启生效。
- **网络模式**（macOS）：一键切到电台的 PPP 网络（经串口线），直接内嵌显示**电台控制面板**（实时信道、频率、电量等）。
- **密码一次**：macOS 切换网络模式需要管理员密码，**只需输入一次**，存在本机钥匙串（Keychain），不再反复输入。
- **通用配置**：`config.json` 配置（路径、DMR ID、呼号、频率、串口），不写死任何设备。
- **跨平台**：macOS `.app` + Windows 启动器（`launch.bat`）。

---

## 要求

| 平台 | 依赖 |
|------|------|
| macOS | Python 3（`/usr/local/bin/python3` 或 `python3`）；MMDVMHost / DMRGateway 二进制 |
| Windows | Python 3（[python.org](https://www.python.org/downloads/)）；MMDVMHost.exe / DMRGateway.exe |

> MMDVMHost / DMRGateway 请从 [g4klx/MMDVMHost](https://github.com/g4klx/MMDVMHost)（含 [W0CHP 改进版](https://github.com/W0CHP/MMDVMHost)）获取，放到任意目录，在配置里填路径即可。

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

---

## 配置

配置文件位置：

- macOS：`~/Library/Application Support/MMDVM-Console/config.json`
- Windows：`%APPDATA%\MMDVM-Console\config.json`

参照 `config.example.json`：

```json
{
  "serial_port": "",                 // 串口，留空自动检测 (macOS: /dev/cu.usbserial-*, Windows: COM*)
  "mmdvm_host_path": "/path/MMDVM-Host",
  "dmrgateway_path": "/path/DMRGateway",
  "mmdvm_ini_path": "/path/MMDVM.ini",
  "dmrgateway_ini_path": "/path/DMRGateway.ini",
  "dmr_id": "4600001",               // 你的 DMR ID
  "callsign": "BG0ABC",
  "frequency_mhz": "438.800",
  "radio_ip": "",                    // 电台网络模式 IP，留空自动由 DMR ID 算出 (12.<ID>)
  "brandmeister": { "server": "4602.master.brandmeister.network", "port": 62031 },
  "web_port": 8080
}
```

> `radio_ip` 留空时自动计算：主机 `12.<DMR ID>`，电台为末字节 ^1（如 DMR ID 8600309 → 主机 `12.131.58.245`、电台 `12.131.58.244`）。

---

## 使用

1. 打开控制台（双击 App / `launch.bat`），浏览器自动打开 `http://localhost:8080/`。
2. macOS 首次切换网络模式会提示**输入管理员密码**（输入一次即可，存钥匙串）。
3. 点 **「切换到网络」** → 界面变为电台控制面板（内嵌）；点 **「切换回热点」** 返回。
4. 热点模式下可 启动 / 停止 / 重启 链路，看状态、通联、日志。

### 网络模式说明（macOS）

- 经串口线建立 PPP，电台 IP 由 DMR ID 决定。
- 切换网络模式需要管理员权限（密码存钥匙串，只输一次）。
- 链路掉线会自动重连（`persist`）。
- **Windows 暂不支持网络模式**（仅热点模式）；如需 PPP，请用 Windows 系统的拨号连接。

---

## 目录结构

```
MMDVM-Console/
├── app/
│   ├── server.py        # 跨平台后端 (配置驱动, 密码一次)
│   ├── index.html       # 前端控制台
│   └── ppp_start.sh     # macOS PPP 启动/停止 (nodetach+persist)
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
