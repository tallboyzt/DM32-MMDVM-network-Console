#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首次启动时生成 config.json（路径用相对值，整个文件夹可以随便复制），
并在换电脑后自动把 MMDVM.ini 里的串口改成实际存在的那个。"""
import json
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "config.json")

CFG = {
    "serial_port": "",
    "mmdvm_host_path": "bin/MMDVMHost.exe",
    "dmrgateway_path": "bin/DMRGateway.exe",
    "mmdvm_ini_path": "mmdvm/MMDVM.ini",
    "dmrgateway_ini_path": "mmdvm/DMRGateway.ini",
    "dmr_id": "4600001",
    "callsign": "N0CALL",
    "frequency_mhz": "438.800",
    "radio_ip": "",
    "brandmeister": {"server": "4602.master.brandmeister.network", "port": 62031},
    "web_port": 8080,
}


def available_ports():
    try:
        from serial.tools import list_ports
        return [p.device for p in list_ports.comports()]
    except Exception:
        return []


def fix_uart_port(root):
    """MMDVM.ini 里的串口在这台电脑上不存在时，换成第一个可用串口。"""
    ini = os.path.join(root, "mmdvm", "MMDVM.ini")
    ports = available_ports()
    if not ports or not os.path.exists(ini):
        return
    with open(ini, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    current = None
    for ln in lines:
        m = re.match(r"\s*UARTPort\s*=\s*(.+?)\s*$", ln)
        if m:
            name = m.group(1).split("\\")[-1].strip()
            current = name.upper()
            break
    if current and current in [p.upper() for p in ports]:
        return
    with open(ini, "w", encoding="utf-8", newline="\r\n") as f:
        for ln in lines:
            if re.match(r"\s*UARTPort\s*=", ln):
                ln = "UARTPort=\\\\.\\%s" % ports[0]
            f.write(ln + "\n")


with open(PATH, "w", encoding="utf-8") as f:
    json.dump(CFG, f, ensure_ascii=False, indent=2)

fix_uart_port(ROOT)
print(PATH)
