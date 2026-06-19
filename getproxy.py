#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCYTHE PROXY MANAGER v10.0 — 7s refresh, multiple sources, state sync
"""
import urllib.request
import ssl
import re
import os
import time
import threading
import random
import hashlib

try:
    from state_manager import state
    STATE_SYNC = True
except ImportError:
    STATE_SYNC = False

# ─── SOURCES ───
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
]

PROXY_FILE = "proxies.txt"
REFRESH_INTERVAL = 7  # 7 seconds

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

class ProxyManager:
    def __init__(self):
        self.proxies = set()
        self.lock = threading.Lock()
        self.running = False
        self.refresh_thread = None
        self.total_fetched = 0

    def extract(self, text):
        pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\:\d{2,5}\b'
        return set(re.findall(pattern, text))

    def fetch(self, url):
        try:
            headers = {
                'User-Agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                ])
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                text = resp.read().decode('utf-8', errors='ignore')
                return self.extract(text)
        except Exception as e:
            print(f"[PROXY] Source failed: {url[:50]}... | {e}")
            return set()

    def refresh(self):
        sources = PROXY_SOURCES.copy()
        random.shuffle(sources)
        new_proxies = set()
        for url in sources:
            fetched = self.fetch(url)
            if fetched:
                new_proxies.update(fetched)
                print(f"[PROXY] {url.split('/')[-1][:15]}: +{len(fetched)}")
            time.sleep(0.5)

        with self.lock:
            before = len(self.proxies)
            self.proxies.update(new_proxies)
            after = len(self.proxies)
            added = after - before
            self.total_fetched += added
            with open(PROXY_FILE, 'w') as f:
                for p in sorted(self.proxies):
                    f.write(p + '\n')

        if STATE_SYNC:
            state.update_proxy_stats(after, self.running, self.total_fetched)
        return added, after

    def start_auto(self):
        if self.running:
            return
        self.running = True
        def loop():
            while self.running:
                try:
                    added, total = self.refresh()
                    print(f"[PROXY] Total: {total} (+{added})")
                except Exception as e:
                    print(f"[PROXY ERROR] {e}")
                time.sleep(REFRESH_INTERVAL)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def stop_auto(self):
        self.running = False

    def get(self):
        with self.lock:
            if not self.proxies:
                return None
            return random.choice(list(self.proxies))

    def count(self):
        with self.lock:
            return len(self.proxies)

    def load(self):
        print("[PROXY] Fetching...")
        added, total = self.refresh()
        print(f"[PROXY] Loaded {total} proxies")
        return total

proxy_manager = ProxyManager()

if __name__ == "__main__":
    print("SCYTHE PROXY MANAGER v10.0")
    proxy_manager.load()
    proxy_manager.start_auto()
    try:
        while True:
            time.sleep(10)
            print(f"[PROXY] Pool: {proxy_manager.count()}")
    except KeyboardInterrupt:
        proxy_manager.stop_auto()
        print("[PROXY] Stopped")