#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MMDVM 控制台 (通用版) — 跨平台后端
- 配置驱动: config.json (MMDVMHost/DMRGateway 路径, DMR ID, 呼号, 频率, 串口)
- 密码一次: macOS sudo 密码存 Keychain (用户输入一次); Windows 无需密码
- 跨平台: macOS (pppd + bash) / Windows (taskkill + exe, 网络模式暂不支持)
用法: python3 server.py [--config PATH]
"""
import json
import os
import re
import sys
import time
import platform
import shlex
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

APP_NAME = "MMDVM-Console"
KEYCHAIN_SERVICE = "mmdvm-console"

CONFIG_PATH = None
MMDVM_LOG = "/tmp/mmdvm.log"
DMRGW_LOG = "/tmp/dmrgateway.log"

DEFAULTS = {
    "serial_port": "",
    "mmdvm_host_path": "",
    "dmrgateway_path": "",
    "mmdvm_ini_path": "",
    "dmrgateway_ini_path": "",
    "dmr_id": "4600001",
    "callsign": "BG0ABC",
    "frequency_mhz": "438.800",
    "radio_ip": "",
    "brandmeister": {"server": "4602.master.brandmeister.network", "port": 62031},
    "web_port": 8080,
}


# ---------- 配置 ----------

def config_dir():
    if IS_WIN:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/Library/Application Support")
    d = os.path.join(base, APP_NAME)
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = os.path.dirname(os.path.abspath(__file__))
    return d


def config_path():
    if CONFIG_PATH:
        return CONFIG_PATH
    return os.path.join(config_dir(), "config.json")


def load_config():
    cfg = dict(DEFAULTS)
    cfg["brandmeister"] = dict(DEFAULTS["brandmeister"])
    try:
        with open(config_path(), encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k == "brandmeister" and isinstance(v, dict):
                cfg["brandmeister"].update(v)
            else:
                cfg[k] = v
    except Exception:
        pass
    return cfg


def save_config(cfg):
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------- 密码 (macOS Keychain, 用户输入一次) ----------

def get_sudo_pw():
    if not IS_MAC:
        return None
    user = os.environ.get("USER", "")
    r = subprocess.run(["security", "find-generic-password", "-a", user,
                        "-s", KEYCHAIN_SERVICE, "-w"], capture_output=True)
    if r.returncode == 0:
        return r.stdout.decode().strip()
    return None


def set_sudo_pw(pw):
    if not IS_MAC:
        return
    user = os.environ.get("USER", "")
    subprocess.run(["security", "add-generic-password", "-a", user,
                    "-s", KEYCHAIN_SERVICE, "-w", pw, "-U"], capture_output=True)


def has_sudo_pw():
    return IS_WIN or (get_sudo_pw() is not None)


def sudo_run(args):
    """macOS: sudo -S 用 Keychain 密码; Windows: 直接运行 (无需密码)。"""
    if IS_WIN:
        r = subprocess.run(args, capture_output=True)
        return r.returncode, r.stdout.decode(errors="replace"), r.stderr.decode(errors="replace")
    pw = get_sudo_pw()
    if pw is None:
        return -1, "", "no password"
    r = subprocess.run(["sudo", "-S", "-p", ""] + list(args),
                       input=(pw + "\n").encode(), capture_output=True)
    return r.returncode, r.stdout.decode(errors="replace"), r.stderr.decode(errors="replace")


# ---------- 设备 / PPP IP ----------

def detect_device():
    if IS_MAC:
        r = subprocess.run("ls /dev/cu.usbserial-* 2>/dev/null", shell=True,
                           capture_output=True, text=True)
        devs = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        return devs[0] if devs else ""
    if IS_WIN:
        for i in range(1, 33):
            if os.path.exists("COM%d" % i):
                return "COM%d" % i
        return ""
    return ""


def get_device():
    dev = load_config().get("serial_port", "").strip()
    if dev:
        return dev
    return detect_device()


def dmr_ips(dmr_id):
    """DMR ID -> (host_ip, radio_ip): host = 12.<ID字节>, 电台 = 末字节^1。"""
    try:
        b = int(dmr_id)
    except Exception:
        b = 0
    b0, b1, b2 = (b >> 16) & 0xFF, (b >> 8) & 0xFF, b & 0xFF
    host = "12.%d.%d.%d" % (b0, b1, b2)
    radio = "12.%d.%d.%d" % (b0, b1, b2 ^ 1)
    return host, radio


def radio_ip():
    cfg = load_config()
    if cfg.get("radio_ip", "").strip():
        return cfg["radio_ip"].strip()
    _, r = dmr_ips(cfg.get("dmr_id", "0"))
    return r


# ---------- 进程控制 ----------

def proc_running(name):
    if IS_WIN:
        r = subprocess.run(["tasklist"], capture_output=True)
        return name.lower() in r.stdout.decode(errors="replace").lower()
    r = subprocess.run(["pgrep", "-x", name], capture_output=True)
    return r.returncode == 0


def proc_kill(name):
    if IS_WIN:
        subprocess.run(["taskkill", "/IM", name + ".exe", "/F"], capture_output=True)
    else:
        subprocess.run(["pkill", "-x", name], capture_output=True)


def chain_names():
    cfg = load_config()
    dg = os.path.basename(cfg.get("dmrgateway_path", "") or "").replace(".exe", "")
    mh = os.path.basename(cfg.get("mmdvm_host_path", "") or "").replace(".exe", "")
    if not dg:
        dg = "DMRGateway"
    if not mh:
        mh = "MMDVM-Host" if IS_MAC else "MMDVMHost"
    return dg, mh


def _spawn(exe, args, log):
    if not exe or not os.path.exists(exe):
        return
    if IS_WIN:
        try:
            with open(log, "w") as f:
                subprocess.Popen([exe] + args, stdout=f, stderr=f,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
    else:
        d = os.path.dirname(exe)
        cmd = "cd %s && exec %s %s > %s 2>&1" % (
            shlex.quote(d), shlex.quote(exe),
            " ".join(shlex.quote(a) for a in args), shlex.quote(log))
        try:
            subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception:
            pass


def fix_device():
    """串口若不可写, 用 sudo chmod 666 (macOS)。"""
    if IS_WIN:
        return
    dev = get_device()
    if not dev:
        return
    try:
        if not os.access(dev, os.W_OK):
            sudo_run(["chmod", "666", dev])
    except Exception:
        pass


def start_chain():
    fix_device()
    cfg = load_config()
    if cfg.get("dmrgateway_path") and cfg.get("dmrgateway_ini_path"):
        _spawn(cfg["dmrgateway_path"], [cfg["dmrgateway_ini_path"]], DMRGW_LOG)
    time.sleep(2)
    if cfg.get("mmdvm_host_path") and cfg.get("mmdvm_ini_path"):
        _spawn(cfg["mmdvm_host_path"], [cfg["mmdvm_ini_path"]], MMDVM_LOG)


def stop_chain():
    dg, mh = chain_names()
    proc_kill(dg)
    proc_kill(mh)


# ---------- PPP (macOS) ----------

def ppp_tool():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ppp_start.sh")


def ppp_sudo(action):
    dev = get_device()
    if not dev:
        return -1, "", "no serial device"
    if IS_WIN:
        return -2, "", "网络模式暂不支持 Windows (仅 macOS)"
    if action == "start":
        rc, out, err = sudo_run(["bash", ppp_tool(), dev])
    else:
        rc, out, err = sudo_run(["bash", ppp_tool(), "--stop"])
    return rc, out, err


# ---------- 模式 ----------

def get_mode():
    cfg = load_config()
    dg, mh = chain_names()
    if proc_running(mh):
        return "hotspot"
    if IS_MAC and proc_running("pppd"):
        return "network"
    return "unknown"


def switch_mode():
    mode = get_mode()
    if mode == "hotspot":
        stop_chain()
        time.sleep(1)
        rc, out, err = ppp_sudo("start")
        return {"mode": "network", "ppp": rc == 0,
                "ppp_out": (out + err).strip() or ("ok" if rc == 0 else "启动失败")}
    if mode == "network":
        rc, out, err = ppp_sudo("stop")
        time.sleep(1)
        start_chain()
        return {"mode": "hotspot", "ppp": rc == 0,
                "ppp_out": (out + err).strip() or ("ok" if rc == 0 else "停止失败")}
    start_chain()
    return {"mode": "hotspot", "ppp": True, "ppp_out": "启动热点"}


# ---------- INI 工具 ----------

def read_ini(path):
    data = {}
    cur = None
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                s = ln.strip()
                if s.startswith("[") and s.endswith("]"):
                    cur = s[1:-1].strip()
                    data[cur] = {}
                elif cur and "=" in s and not s.startswith("#") and not s.startswith(";"):
                    k, v = s.split("=", 1)
                    data[cur][k.strip()] = v.strip()
    except Exception:
        pass
    return data


def update_ini(path, section, key, value):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return False
    cur = None
    out = []
    changed = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            cur = s[1:-1].strip()
            out.append(ln)
            continue
        if cur == section and s.startswith(key + "="):
            out.append("%s=%s" % (key, value))
            changed = True
            continue
        out.append(ln)
    if not changed:
        idx = None
        for i, ln in enumerate(out):
            s = ln.strip()
            if s.startswith("[") and s.endswith("]") and s[1:-1].strip() == section:
                idx = i
                break
        if idx is not None:
            j = idx + 1
            while j < len(out):
                s = out[j].strip()
                if s.startswith("[") and s.endswith("]"):
                    break
                j += 1
            out.insert(j, "%s=%s" % (key, value))
            changed = True
    if changed:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(out) + "\n")
        except Exception:
            pass
    return changed


def apply_ini(updates):
    cfg = load_config()
    ini_paths = {"mmdvm": cfg.get("mmdvm_ini_path", ""),
                 "dmrgateway": cfg.get("dmrgateway_ini_path", "")}
    done = []
    for u in updates:
        f = u.get("file")
        section = u.get("section")
        key = u.get("key")
        value = str(u.get("value", ""))
        path = ini_paths.get(f, "")
        if not path or not section or not key:
            continue
        if update_ini(path, section, key, value):
            done.append("%s.%s.%s=%s" % (f, section, key, value))
    return done


def get_config():
    cfg = load_config()
    mm = read_ini(cfg.get("mmdvm_ini_path", ""))
    dg = read_ini(cfg.get("dmrgateway_ini_path", ""))
    dg1 = dg.get("DMR Network 1", {})
    mm_dn = mm.get("DMR Network", {})
    return {
        "mmdvm": {
            "General": {"Callsign": mm.get("General", {}).get("Callsign", ""),
                        "Id": mm.get("General", {}).get("Id", ""),
                        "Duplex": mm.get("General", {}).get("Duplex", "0")},
            "Modem": {"UARTPort": mm.get("Modem", {}).get("UARTPort", ""),
                      "RXFrequency": mm.get("Modem", {}).get("RXFrequency", ""),
                      "TXFrequency": mm.get("Modem", {}).get("TXFrequency", "")},
            "DMR": {"ColorCode": mm.get("DMR", {}).get("ColorCode", "")},
            "DMR Network": {"Enable": mm_dn.get("Enable", ""),
                            "GatewayAddress": mm_dn.get("GatewayAddress", ""),
                            "GatewayPort": mm_dn.get("GatewayPort", ""),
                            "Slot1": mm_dn.get("Slot1", ""),
                            "Slot2": mm_dn.get("Slot2", "")},
        },
        "dmrgateway": {
            "General": {"Id": dg.get("General", {}).get("Id", "")},
            "Info": {"Callsign": dg.get("Info", {}).get("Callsign", ""),
                     "TXFrequency": dg.get("Info", {}).get("TXFrequency", ""),
                     "RXFrequency": dg.get("Info", {}).get("RXFrequency", ""),
                     "Duplex": dg.get("Info", {}).get("Duplex", "0"),
                     "ColorCode": dg.get("Info", {}).get("ColorCode", ""),
                     "Slot1": dg.get("Info", {}).get("Slot1", ""),
                     "Slot2": dg.get("Info", {}).get("Slot2", "")},
            "DMR Network 1": {"Enabled": dg1.get("Enabled", ""),
                              "Name": dg1.get("Name", ""),
                              "Address": dg1.get("Address", ""),
                              "Port": dg1.get("Port", ""),
                              "Password": dg1.get("Password", "")},
        },
    }


# ---------- 日志解析 (QSO) ----------

QSO_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2})\s+.*?\b(\d{7})\b.*?\b(\d{7})\b.*?\b(\d{1,3})\b.*?"
    r"(\d{1,3}(?:\.\d+)?)\s*/\s*(\d{1,3}(?:\.\d+)?)", re.I)


def parse_qso(path):
    qsos = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-200:]
    except Exception:
        return qsos
    for ln in lines:
        m = QSO_RE.search(ln)
        if m:
            qsos.append({"t": m.group(1), "src": m.group(2), "dst": m.group(3),
                         "ts": m.group(4), "rssi": "%s/%s" % (m.group(5), m.group(6))})
    return qsos[-30:]


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _page(self, html):
        self._send(200, html.encode(), "text/html; charset=utf-8")

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            return json.loads(self.rfile.read(n).decode()) if n else {}
        except Exception:
            return {}

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            self._page(index_html())
        elif p == "/api/status":
            self._json(status())
        elif p == "/api/info":
            self._json(info())
        elif p == "/api/mode":
            self._json({"mode": get_mode(), "device": get_device()})
        elif p == "/api/config":
            self._json(get_config())
        elif p == "/api/password":
            self._json({"set": has_sudo_pw(), "platform": "mac" if IS_MAC else "win"})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        p = urlparse(self.path).path
        data = self._body()
        if p == "/api/switch":
            self._json(switch_mode())
        elif p == "/api/start":
            start_chain()
            self._json({"ok": True})
        elif p == "/api/stop":
            stop_chain()
            self._json({"ok": True})
        elif p == "/api/restart":
            stop_chain()
            time.sleep(2)
            start_chain()
            self._json({"ok": True})
        elif p == "/api/config":
            updates = data.get("updates", [])
            ini_done = apply_ini([u for u in updates if u.get("file")])
            cfg = load_config()
            done = []
            for it in updates:
                if it.get("file"):
                    continue
                k, v = it.get("key"), it.get("value")
                if k in cfg and k != "brandmeister":
                    cfg[k] = v
                    done.append(k)
            save_config(cfg)
            self._json({"ok": True, "applied": done, "ini": ini_done})
        elif p == "/api/password":
            pw = data.get("password", "")
            if pw:
                set_sudo_pw(pw)
            self._json({"ok": True, "set": has_sudo_pw()})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        pass


# ---------- 状态 ----------

def info():
    cfg = load_config()
    return {
        "mode": get_mode(),
        "device": get_device(),
        "callsign": cfg.get("callsign", ""),
        "frequency_mhz": cfg.get("frequency_mhz", ""),
        "dmr_id": cfg.get("dmr_id", ""),
        "radio_ip": radio_ip(),
        "password_set": has_sudo_pw(),
        "platform": "mac" if IS_MAC else "win",
        "configured": bool(cfg.get("mmdvm_host_path") and cfg.get("mmdvm_ini_path")),
    }


def status():
    cfg = load_config()
    mmdvm_ini = cfg.get("mmdvm_ini_path", "")
    dg, mh = chain_names()
    ini = read_ini(mmdvm_ini) if mmdvm_ini else {}
    return {
        "mode": get_mode(),
        "running": {"dmrgateway": proc_running(dg), "mmdvmhost": proc_running(mh)},
        "info": {
            "callsign": ini.get("General", {}).get("Callsign", cfg.get("callsign", "")),
            "frequency": cfg.get("frequency_mhz", ""),
            "dmr_id": cfg.get("dmr_id", ""),
            "radio_ip": radio_ip(),
        },
        "config": ini.get("General", {}),
        "qsos": parse_qso(MMDVM_LOG),
        "mmdvm_log": tail_log(MMDVM_LOG),
        "dmrgateway_log": tail_log(DMRGW_LOG),
    }


def tail_log(path, n=100):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""


# ---------- 前端 ----------

def index_html():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>MMDVM 控制台</h1><p>index.html 未找到</p>"


def main():
    global CONFIG_PATH
    args = sys.argv[1:]
    if "--config" in args:
        CONFIG_PATH = args[args.index("--config") + 1]
    port = int(load_config().get("web_port", 8080))
    print("MMDVM 控制台: http://localhost:%d" % port)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
