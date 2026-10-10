#!/usr/bin/env python
"""
Minecraft Server Dashboard v2.1
http://localhost:58888
"""
import threading, time, json, struct, sys, io, os, re
from flask import Flask, jsonify, request

try:
    import paramiko
except ImportError:
    print("pip install paramiko flask")
    sys.exit(1)

app = Flask(__name__)

SSH_HOST = "mc.furina.fun"
SSH_USER = "mcpanel"
SSH_PASSWORD = "{{MCPANEL_PASSWORD}}"
RCON_PASSWORD = "{{RCON_PASSWORD}}"
RCON_PORT = 25575

# ============ SSH & RCON ============

def _new_ssh():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=8)
    return c

def ssh_exec(cmd, timeout=12):
    c = None
    try:
        c = _new_ssh()
        stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors='replace').strip()
        err = stderr.read().decode(errors='replace').strip()
        return (out + '\n' + err).strip() if err else out
    except Exception as e:
        return f"SSH_ERROR: {e}"
    finally:
        try: c.close()
        except: pass

def rcon_send(cmd):
    """每次调用新建 SSH 隧道 + RCON 连接，用完即关"""
    c = None
    ch = None
    try:
        c = _new_ssh()
        transport = c.get_transport()
        ch = transport.open_channel("direct-tcpip", ("127.0.0.1", RCON_PORT), ("127.0.0.1", 0))
        ch.settimeout(8)

        def send(typ, body):
            rid = int(time.time() * 1000) & 0x7FFFFFFF
            payload = body.encode('utf-8') + b'\x00\x00'
            pkt = struct.pack('<iii', 4+4+len(payload), rid, typ) + payload
            ch.sendall(pkt)
            return rid

        def recv():
            data = b''
            while len(data) < 4:
                chunk = ch.recv(4 - len(data))
                if not chunk: return None
                data += chunk
            length = struct.unpack('<i', data)[0]
            while len(data) < 4 + length:
                chunk = ch.recv(4 + length - len(data))
                if not chunk: return None
                data += chunk
            return data[12:12+length-10].decode('utf-8', errors='replace') if length >= 10 else ""

        send(3, RCON_PASSWORD)
        recv()
        send(2, cmd)
        return recv() or "(无输出)"
    except Exception as e:
        return f"RCON错误: {e}"
    finally:
        try: ch.close()
        except: pass
        try: c.close()
        except: pass

# ============ 模组映射 ============
MOD_INFO = {
    "balm": {"name": "BALM", "desc": "前置库 - 模组开发框架", "icon": "📦"},
    "lithium": {"name": "Lithium", "desc": "性能优化 - 提升服务器TPS", "icon": "⚡"},
    "LuckPerms": {"name": "LuckPerms", "desc": "权限管理 - 分组/前缀/权限控制", "icon": "🔐"},
    "servercore": {"name": "ServerCore", "desc": "服务器工具 - TPA/Home/传送", "icon": "🛠️"},
    "shogi": {"name": "Shogi", "desc": "BALM配套 - 配置与网络", "icon": "📡"},
    "voicechat": {"name": "Simple Voice Chat", "desc": "语音聊天 - 游戏内语音通话", "icon": "🎤"},
    "waystones": {"name": "Waystones", "desc": "传送石碑 - 快速旅行点", "icon": "🗿"},
    "worldedit": {"name": "WorldEdit", "desc": "创世神 - 游戏内地图编辑器", "icon": "🌍"},
}

def parse_mod_name(filename):
    name = filename.replace('.jar', '').replace('.jar.disabled', '')
    for key, info in MOD_INFO.items():
        if key.lower() in name.lower():
            return info["name"], info["desc"], info["icon"]
    short = re.sub(r'-\d+\.\d+.*$', '', name)
    return short, "未知模组", "❓"

# ============ API ============

@app.route('/')
def index():
    return HTML

@app.route('/api/status')
def api_status():
    result = {"online": False, "players": 0, "max_players": 20,
              "mem_used": "?", "mem_total": "?", "cpu": "?", "uptime": "?",
              "player_list": [], "server_time": time.strftime("%H:%M:%S")}

    active = ssh_exec("sudo systemctl is-active minecraft")
    result["online"] = ("active" in active)

    if result["online"]:
        mem_out = ssh_exec("free -m | awk '/^Mem:/{print $3,$2}'")
        if mem_out and not mem_out.startswith("SSH_ERROR"):
            parts = mem_out.split()
            if len(parts) >= 2:
                result["mem_used"], result["mem_total"] = parts[0], parts[1]

        uptime_out = ssh_exec("uptime -p")
        if uptime_out and not uptime_out.startswith("SSH_ERROR"):
            result["uptime"] = uptime_out.replace("up ", "")

        cpu_out = ssh_exec("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
        if cpu_out and not cpu_out.startswith("SSH_ERROR"):
            result["cpu"] = cpu_out.strip('%')

        player_out = rcon_send("list")
        if player_out and "There are" in player_out:
            parts = player_out.split()
            try:
                result["players"] = int(parts[2])
                result["max_players"] = int(parts[6])
            except: pass
            if ":" in player_out:
                names_str = player_out.split(":", 1)[1].strip()
                result["player_list"] = [n.strip() for n in names_str.split(",") if n.strip()]

    return jsonify(result)

@app.route('/api/logs')
def api_logs():
    raw = ssh_exec("grep -v 'Thread RCON Client' /opt/minecraft/logs/latest.log | tail -80")
    lines = raw.split("\n")
    filtered = []
    key_patterns = [
        r'joined the game', r'left the game', r'lost connection',
        r'<[^>]+>\s',
        r'\[ERROR\]', r'ERROR', r'FATAL', r'CRASH',
        r'\[WARN\]', r'WARN',
        r'Starting minecraft', r'Done', r'Stopping',
        r'Saving', r'Saved the game',
        r'voicechat.*successfully connected', r'voicechat.*Disconnecting',
        r'logged in',
        r'has made the advancement',
        r'moved to world',
        r'Saving chunks for level.*minecraft',
    ]
    def fmt(line):
        ts_m = re.match(r'\[(\d{2}\w{3}\d{4} \d{2}:\d{2}:\d{2})\.\d+\]', line)
        ts_str = ts_m.group(1) if ts_m else ''
        clean = re.sub(r'^(\[.*?\]\s*){3}', '', line)
        if ts_str:
            from datetime import datetime
            try:
                dt = datetime.strptime(ts_str, '%d%b%Y %H:%M:%S')
                ts_str = dt.strftime('%m-%d %H:%M:%S')
            except: pass
        ts_display = f'[{ts_str}]' if ts_str else ''
        if 'has made the advancement' in clean:
            return f'{ts_display} \U0001f3c6 {clean}'
        dim = ''
        if 'the_nether' in line:
            dim = '\U0001f525'
        elif 'the_end' in line:
            dim = '\U0001f31f'
        elif 'overworld' in line:
            dim = '\U0001f30d'
        prefix = f'[{dim}] ' if dim else ''
        return f'{ts_display} {prefix}{clean}'
    for line in lines:
        if 'waystones-common.toml is not correct' in line:
            continue
        for pat in key_patterns:
            if re.search(pat, line):
                filtered.append(fmt(line))
                break
    return jsonify({"logs": "\n".join(filtered[-30:]) or "(\u6682\u65e0\u91cd\u8981\u65e5\u5fd7)"})

@app.route('/api/mods')
def api_mods():
    mods = ssh_exec("ls -1 /opt/minecraft/mods/")
    result = []
    if mods and not mods.startswith("SSH_ERROR"):
        for f in sorted(mods.split('\n')):
            f = f.strip()
            if not f: continue
            disabled = f.endswith('.disabled')
            name, desc, icon = parse_mod_name(f)
            ver_match = re.search(r'-(\d+\.\d+[^.]*(?:\.\d+)*)', f.replace('.disabled',''))
            version = ver_match.group(1) if ver_match else "?"
            result.append({
                "file": f, "name": name, "desc": desc, "icon": icon,
                "version": version, "enabled": not disabled
            })
    return jsonify({"mods": result})

@app.route('/api/mods/toggle', methods=['POST'])
def api_mods_toggle():
    data = request.get_json()
    filename = data.get('file', '')
    enable = data.get('enable', True)
    base = "/opt/minecraft/mods/"
    if enable:
        newname = filename.replace('.jar.disabled', '.jar')
    else:
        if filename.endswith('.jar.disabled'):
            return jsonify({"ok": False, "msg": "已经禁用"})
        newname = filename + '.disabled'
    out = ssh_exec(f"mv '{base}{filename}' '{base}{newname}' 2>&1 && echo OK")
    return jsonify({"ok": "OK" in out, "need_restart": True,
                    "msg": "已切换，需重启生效" if "OK" in out else out})

@app.route('/api/start')
def api_start():
    ssh_exec("sudo systemctl start minecraft")
    time.sleep(8)
    active = ssh_exec("sudo systemctl is-active minecraft")
    return jsonify({"ok": "active" in active})

@app.route('/api/stop')
def api_stop():
    rcon_send("stop")
    time.sleep(10)
    ssh_exec("sudo systemctl stop minecraft")
    time.sleep(3)
    active = ssh_exec("sudo systemctl is-active minecraft")
    return jsonify({"ok": "inactive" in active})

@app.route('/api/restart')
def api_restart():
    ssh_exec("sudo systemctl restart minecraft")
    time.sleep(12)
    active = ssh_exec("sudo systemctl is-active minecraft")
    return jsonify({"ok": "active" in active})

@app.route('/api/command', methods=['POST'])
def api_command():
    data = request.get_json()
    cmd = data.get('cmd', '')
    if not cmd: return jsonify({"ok": False, "output": "指令为空"})
    output = rcon_send(cmd)
    return jsonify({"ok": not output.startswith("RCON"), "output": output})

# ============ DDNS 状态 ============

@app.route('/api/ddns')
def api_ddns():
    result = {
        "current_ip": "?", "dns_ip": "?", "in_sync": False,
        "last_check": "?", "last_action": "?",
        "cron_active": False, "updater_status": "未知",
        "logs": []
    }

    # 读 DDNS 日志
    log_out = ssh_exec("tail -20 /home/mcpanel/ddns/ddns.log 2>&1")
    if log_out and not log_out.startswith("SSH_ERROR"):
        result["logs"] = [l.strip() for l in log_out.split("\n") if l.strip()][-12:]

        # 从日志中提取状态
        for line in reversed(result["logs"]):
            if "当前公网 IP:" in line:
                result["current_ip"] = line.split("当前公网 IP:")[-1].strip()
            if "DNS 解析 IP:" in line:
                dns_raw = line.split("DNS 解析 IP:")[-1].strip()
                result["dns_ip"] = dns_raw if dns_raw else "未解析"
            if "IP 未变化" in line:
                result["last_action"] = "未变化"
                result["in_sync"] = True
            if "DNS 更新成功" in line:
                result["last_action"] = "已更新"
                result["in_sync"] = True
            if "ERROR" in line or "失败" in line:
                result["last_action"] = "异常"
                result["in_sync"] = False
            if result["current_ip"] != "?" and result["dns_ip"] != "?" and result["last_action"] != "?":
                break

        # 从时间戳提取 last_check
        for line in reversed(result["logs"]):
            m = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if m:
                result["last_check"] = m.group(1)
                break

    # 检查 crontab 是否活跃
    cron_out = ssh_exec("crontab -l 2>&1 | grep ddns")
    result["cron_active"] = "ddns" in cron_out if cron_out else False
    result["updater_status"] = "活跃" if result["cron_active"] else "未配置"

    # 如果 in_sync 但 current_ip == dns_ip == "?"，说明还没运行过
    if result["current_ip"] == "?" and result["dns_ip"] == "?":
        result["last_action"] = "等待首次检测"

    return jsonify(result)

# ============ 诊断报告 ============
_diagnostic_results = {}  # id -> report (内存存储，重启清空)
_last_diagnostic = None   # 最新的一个报告

@app.route('/api/diagnostic', methods=['GET', 'POST'])
def api_diagnostic():
    global _diagnostic_results, _last_diagnostic
    if request.method == 'POST':
        data = request.get_json()
        report = data.get("report", {})
        rid = report.get("id", str(int(time.time())))
        report["_received_at"] = time.strftime("%H:%M:%S")
        _diagnostic_results[rid] = report
        _last_diagnostic = report
        # 只保留最近 50 条
        if len(_diagnostic_results) > 50:
            oldest = sorted(_diagnostic_results.keys())[0]
            del _diagnostic_results[oldest]
        return jsonify({"ok": True, "msg": "报告已接收", "id": rid})
    else:
        # GET: 返回列表或单个报告
        rid = request.args.get("id")
        if rid and rid in _diagnostic_results:
            return jsonify({"report": _diagnostic_results[rid]})
        # 返回所有报告摘要列表
        summary_list = []
        for rid in sorted(_diagnostic_results.keys(), reverse=True):
            r = _diagnostic_results[rid]
            summary_list.append({
                "id": rid,
                "player_name": r.get("player_name", "?"),
                "time": r.get("time", "?"),
                "server": r.get("server", "?"),
                "score": r.get("score", 0),
                "grade": r.get("grade", "?"),
                "status": r.get("status", "?"),
                "_received_at": r.get("_received_at", "?"),
            })
        return jsonify({"reports": summary_list, "count": len(summary_list)})

# ============ 前端 ============
def _load_html():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()
HTML = _load_html()

if __name__ == '__main__':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        print("=" * 50)
        print("  MC Dashboard v2.1")
        print("  http://localhost:58888")
        print("=" * 50)
    except (AttributeError, ValueError):
        pass  # pythonw 无控制台，跳过
    app.run(host='127.0.0.1', port=58888, debug=False, threaded=True)
