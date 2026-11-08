#!/bin/bash
# ppp_start.sh — 启动/停止 macOS PPP 连接 (电台网络模式)
# 用法: ppp_start.sh <串口>        # 启动 PPP
#       ppp_start.sh --stop        # 停止 PPP
# 需要 root (sudo)。nodetach + persist: 掉线自动重连。
set -u
PORT="${1:-}"

stop_ppp() {
    # 停止 pppd (unit 7)
    /usr/sbin/pppd /dev/null 2>/dev/null
    /bin/kill "$(cat /tmp/pppd.pid 2>/dev/null)" 2>/dev/null
    /usr/bin/pkill -x pppd 2>/dev/null
    /sbin/route -q delete -net 12.0.0.0/8 -interface ppp7 2>/dev/null
    /sbin/route -q delete -net 225.0.0.0/8 -interface ppp7 2>/dev/null
    exit 0
}

if [ "$PORT" = "--stop" ]; then
    stop_ppp
fi

if [ -z "$PORT" ]; then
    echo "用法: ppp_start.sh <串口>" >&2
    exit 1
fi

# 先停掉旧的
/usr/bin/pkill -x pppd 2>/dev/null
sleep 1

# 后台启动 pppd (nodetach: 不 fork, 避免 Apple pppd 崩溃; persist: 掉线自动重连)
nohup /usr/sbin/pppd "$PORT" 115200 noauth local nocrtscts noipdefault nodefaultroute novj noccp \
  lcp-echo-interval 10 lcp-echo-failure 3 unit 7 nodetach persist >/tmp/pppd.log 2>&1 &
echo $! > /tmp/pppd.pid

# 等待 ppp7 起来 (最多 30s)
for i in $(seq 1 30); do
    if /sbin/ifconfig ppp7 2>/dev/null | grep -q "inet "; then
        break
    fi
    sleep 1
done

# 加路由
/sbin/route -q add -net 12.0.0.0/8 -interface ppp7 2>/dev/null
/sbin/route -q add -net 225.0.0.0/8 -interface ppp7 2>/dev/null
/sbin/ifconfig ppp7 2>/dev/null | grep "inet " || echo "ppp7 未就绪"
