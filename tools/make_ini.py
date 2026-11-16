#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 g4klx 源码自带的 ini 样例生成 Windows 热点用的 MMDVM.ini / DMRGateway.ini"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "mmdvm")


def edit_ini(src_path, dst_path, values):
    with open(src_path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    section = None
    applied = set()
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1].strip()
            out.append(ln)
            continue
        if section in values and "=" in s and not s.startswith("#"):
            key = s.split("=", 1)[0].strip()
            if key in values[section]:
                out.append("%s=%s" % (key, values[section][key]))
                applied.add((section, key))
                continue
        out.append(ln)
    # 追加样例里没有的键
    for sec, kv in values.items():
        missing = [(k, v) for k, v in kv.items() if (sec, k) not in applied]
        if not missing:
            continue
        idx = None
        for i, ln in enumerate(out):
            s = ln.strip()
            if s.startswith("[") and s.endswith("]") and s[1:-1].strip() == sec:
                idx = i
                break
        if idx is None:
            out.append("[%s]" % sec)
            idx = len(out) - 1
        j = idx + 1
        while j < len(out):
            s = out[j].strip()
            if s.startswith("[") and s.endswith("]"):
                break
            j += 1
        for k, v in missing:
            out.insert(j, "%s=%s" % (k, v))
            j += 1
    with open(dst_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(out) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    edit_ini(os.path.join(SRC, "MMDVM-Host", "MMDVM-Host.ini"),
             os.path.join(OUT, "MMDVM.ini"), {
        "General": {"Callsign": "N0CALL", "Id": "4600001", "Duplex": "0"},
        "Log": {"DisplayLevel": "1", "MQTTLevel": "0"},
        "CW Id": {"Enable": "0"},
        "DMR Id Lookup": {"File": "DMRIds.dat", "Time": "0"},
        "Modem": {"Protocol": "uart", "UARTPort": "\\\\.\\COM3", "UARTSpeed": "115200",
                  "RXFrequency": "438800000", "TXFrequency": "438800000"},
        "DMR": {"Enable": "1", "ColorCode": "1"},
        "POCSAG": {"Enable": "0"},
        "FM": {"Enable": "0"},
        "DMR Network": {"Enable": "1", "LocalAddress": "127.0.0.1", "LocalPort": "62032",
                        "GatewayAddress": "127.0.0.1", "GatewayPort": "62031",
                        "Slot1": "0", "Slot2": "1"},
        "POCSAG Network": {"Enable": "0"},
        "FM Network": {"Enable": "0"},
    })

    edit_ini(os.path.join(SRC, "DMRGateway", "DMRGateway.ini"),
             os.path.join(OUT, "DMRGateway.ini"), {
        "General": {"Id": "4600001", "Timeout": "10", "RptAddress": "127.0.0.1",
                    "RptPort": "62032", "LocalAddress": "127.0.0.1", "LocalPort": "62031"},
        "Log": {"DisplayLevel": "1", "MQTTLevel": "0"},
        "Voice": {"Enabled": "0"},
        "Info": {"Callsign": "N0CALL", "TXFrequency": "438800000", "RXFrequency": "438800000",
                 "Power": "1", "ColorCode": "1", "Duplex": "0", "Slot1": "0", "Slot2": "1"},
        "XLX Network": {"Enabled": "0"},
        "DMR Network 1": {"Enabled": "1", "Name": "BM",
                          "Address": "4602.master.brandmeister.network", "Port": "62031",
                          "Password": "CHANGEME"},
        "DMR Network 2": {"Enabled": "0"},
        "DMR Network 3": {"Enabled": "0"},
        "DMR Network 4": {"Enabled": "0"},
        "DMR Network 5": {"Enabled": "0"},
    })
    print("wrote", OUT)


if __name__ == "__main__":
    main()
