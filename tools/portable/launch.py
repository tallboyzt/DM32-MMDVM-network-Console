#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""便携版启动器：检查配置 → 后台拉起 server.py（独立小窗口）→ 打开浏览器。"""
import json
import os
import socket
import subprocess
import sys
import time
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config.json")
SERVER = os.path.join(ROOT, "app", "server.py")
INIT = os.path.join(ROOT, "tools", "init_config.py")
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "MMDVM-Console", "logs")


def ensure_config():
    if not os.path.exists(CFG):
        subprocess.run([sys.executable, INIT, ROOT], check=False)


def read_port():
    try:
        with open(CFG, encoding="utf-8") as f:
            return int(json.load(f).get("web_port", 8080) or 8080)
    except Exception:
        return 8080


def port_open(port):
    s = socket.socket()
    s.settimeout(0.8)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def main():
    ensure_config()
    port = read_port()
    if not port_open(port):
        wrapper = subprocess.Popen(
            ["cmd", "/c", "start", "MMDVM Console", "/min",
             sys.executable, SERVER, "--config", CFG],
            cwd=ROOT,
        )
        try:
            wrapper.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        for _ in range(80):
            if port_open(port):
                break
            time.sleep(0.25)
        else:
            print("控制台没有启动成功。请查看日志: %s" % LOG_DIR)
            return 1
    webbrowser.open("http://127.0.0.1:%d/" % port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
