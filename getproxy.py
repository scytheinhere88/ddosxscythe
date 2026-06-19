#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCYTHE PROXY MANAGER v11.0 — Advanced Scraper + Auto-Refresh + State Sync
Uses robust scraping with rotating headers, multiple sources, deduplication.
"""
import os
import sys
import time
import json
import re
import random
import threading
import socket
import ssl
import urllib.request
import requests
from bs4 import BeautifulSoup
import datetime
import pytz

try:
    from state_manager import state
    STATE_SYNC = True
except ImportError:
    STATE_SYNC = False

# ─── Configuration ───
PROXY_FILE = "proxies.txt"
REFRESH_INTERVAL = 7  # seconds

# ─── Source URLs (from old file) ───
PROXY_SOURCES = [
    "https://api.proxies.is/scraped?token=7k6e6J11371Y8H6whs0bc&timeout=15000&excludeASN=&includeASN=&excludeCountry=&includeCountry=VN&type=",
    "https://api.proxies.is/scraped?token=7k6e6J11371Y8H6whs0bc&timeout=15000&excludeASN=&includeASN=&excludeCountry=&includeCountry=ID&type=",
    "https://api.proxies.is/scraped?token=7k6e6J11371Y8H6whs0bc&timeout=15000&excludeASN=&includeASN=&excludeCountry=&includeCountry=&type=",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
]

# ─── Color codes ───
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# ─── Proxy extraction (from old file, optimized) ───
def extract_proxies_from_text(text_content):
    found_proxies = set()
    ip_pattern = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    port_pattern = r'(?:[1-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])'
    auth_pattern = r'[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+@'
    domain_or_ip_pattern = r'(?:' + ip_pattern + r'|(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6})'
    proxy_pattern_url_capture = r'(?:https?://|socks4://|socks5://)?(' + auth_pattern + domain_or_ip_pattern + r':' + port_pattern + r'|' + ip_pattern + r':' + port_pattern + r')\b'
    proxy_pattern_ip_port = r'\b' + ip_pattern + r':' + port_pattern + r'\b'

    # Regex matches
    for match in re.findall(proxy_pattern_url_capture, text_content):
        found_proxies.add(match.strip())
    for match in re.findall(proxy_pattern_ip_port, text_content):
        found_proxies.add(match.strip())

    # Line-by-line parsing for custom formats
    for line in text_content.splitlines():
        stripped = line.strip()
        if not stripped: continue
        if "Bookmark and Share" in stripped or "Let Snatcher find FREE PROXY LISTS" in stripped or "##" in stripped:
            continue
        parts = stripped.split(':')
        if len(parts) == 4:
            ip_check, port_check = parts[0], parts[1]
            if re.fullmatch(ip_pattern, ip_check) and re.fullmatch(port_pattern, port_check):
                found_proxies.add(f"{parts[2]}:{parts[3]}@{ip_check}:{port_check}")
        elif len(parts) == 2:
            ip_part, port_part = parts
            if re.fullmatch(ip_pattern, ip_part) and re.fullmatch(port_pattern, port_part):
                found_proxies.add(stripped)
        elif len(parts) >= 3 and '@' in stripped:
            match = re.search(proxy_pattern_url_capture, stripped)
            if match:
                found_proxies.add(match.group(1).strip())

    # JSON parsing
    try:
        json_data = json.loads(text_content)
        if isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, dict):
                    if 'proxy_address' in item and 'port' in item:
                        ip = item['proxy_address']
                        port = item['port']
                        user = item.get('username')
                        pwd = item.get('password')
                        if (re.fullmatch(ip_pattern, str(ip)) or re.fullmatch(domain_or_ip_pattern, str(ip))) and re.fullmatch(port_pattern, str(port)):
                            if user and pwd:
                                found_proxies.add(f"{user}:{pwd}@{ip}:{port}")
                            else:
                                found_proxies.add(f"{ip}:{port}")
                    elif 'ip' in item and 'port' in item:
                        ip = item['ip']
                        port = item['port']
                        user = item.get('username') or item.get('user')
                        pwd = item.get('password') or item.get('pass')
                        if (re.fullmatch(ip_pattern, str(ip)) or re.fullmatch(domain_or_ip_pattern, str(ip))) and re.fullmatch(port_pattern, str(port)):
                            if user and pwd:
                                found_proxies.add(f"{user}:{pwd}@{ip}:{port}")
                            else:
                                found_proxies.add(f"{ip}:{port}")
                    elif 'proxy' in item and isinstance(item['proxy'], str):
                        match = re.search(proxy_pattern_url_capture, item['proxy'])
                        if match:
                            found_proxies.add(match.group(1).strip())
                elif isinstance(item, str):
                    match = re.search(proxy_pattern_url_capture, item)
                    if match:
                        found_proxies.add(match.group(1).strip())
        elif isinstance(json_data, dict):
            if 'results' in json_data and isinstance(json_data['results'], list):
                for item in json_data['results']:
                    if isinstance(item, dict):
                        if 'proxy_address' in item and 'port' in item:
                            ip = item['proxy_address']
                            port = item['port']
                            user = item.get('username')
                            pwd = item.get('password')
                            if (re.fullmatch(ip_pattern, str(ip)) or re.fullmatch(domain_or_ip_pattern, str(ip))) and re.fullmatch(port_pattern, str(port)):
                                if user and pwd:
                                    found_proxies.add(f"{user}:{pwd}@{ip}:{port}")
                                else:
                                    found_proxies.add(f"{ip}:{port}")
            for key, value in json_data.items():
                if isinstance(value, str):
                    match = re.search(proxy_pattern_url_capture, value)
                    if match:
                        found_proxies.add(match.group(1).strip())
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            match = re.search(proxy_pattern_url_capture, item)
                            if match:
                                found_proxies.add(match.group(1).strip())
    except:
        pass

    # Cleanup
    cleaned = set()
    for p in found_proxies:
        if "0.0.0.0:" not in p and p != "0.0.0.0:0":
            if "://" in p:
                cleaned.add(p.split('://', 1)[1])
            else:
                cleaned.add(p)
    return [p for p in cleaned if p]

# ─── Fetch from single URL (with anti-honeypot headers) ───
def fetch_proxies_from_url(url, timeout=30):
    browser_fingerprints = [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8',
            'Sec-Ch-Ua': '"Chromium";v="121", "Google Chrome";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Connection': 'keep-alive'
        }
    ]
    popular_referers = ['https://www.google.com/', 'https://www.bing.com/', 'https://duckduckgo.com/', 'https://github.com/']
    headers = random.choice(browser_fingerprints).copy()
    headers['Referer'] = random.choice(popular_referers)

    try:
        with requests.Session() as session:
            response = session.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '').lower()
            content = response.text
            proxies = extract_proxies_from_text(content)
            # If HTML, also parse with BeautifulSoup
            if 'html' in content_type:
                soup = BeautifulSoup(content, 'html.parser')
                for tag in soup.find_all(['pre', 'textarea', 'code', 'div', 'p', 'table', 'tr']):
                    text_from_tag = tag.get_text()
                    if "Bookmark and Share" not in text_from_tag and "Let Snatcher find FREE PROXY LISTS" not in text_from_tag and "##" not in text_from_tag:
                        proxies.extend(extract_proxies_from_text(text_from_tag))
            return list(set(proxies))  # dedup
    except Exception as e:
        print(f"[PROXY] Source failed: {url[:50]}... | {e}")
        return []

# ─── Main scraper (collects from all sources) ───
def scrape_all_sources():
    all_proxies = []
    for url in PROXY_SOURCES:
        print(f"[PROXY] Scraping: {url[:50]}...")
        fetched = fetch_proxies_from_url(url)
        if fetched:
            all_proxies.extend(fetched)
            print(f"[PROXY] +{len(fetched)} proxies")
        time.sleep(1)  # slight delay between sources
    # Deduplicate
    unique = list(set(all_proxies))
    return unique

# ─── ProxyManager class ───
class ProxyManager:
    def __init__(self):
        self.proxies = set()
        self.lock = threading.Lock()
        self.running = False
        self.refresh_thread = None
        self.total_fetched = 0

    def _load_from_file(self):
        if os.path.exists(PROXY_FILE):
            try:
                with open(PROXY_FILE, 'r') as f:
                    proxies = [l.strip() for l in f if l.strip()]
                with self.lock:
                    self.proxies.update(proxies)
            except:
                pass

    def refresh(self):
        print("[PROXY] Refreshing proxy pool...")
        new_proxies = scrape_all_sources()
        if not new_proxies:
            print("[PROXY] No new proxies scraped. Keeping existing pool.")
            return 0, len(self.proxies)

        with self.lock:
            before = len(self.proxies)
            self.proxies.update(new_proxies)
            after = len(self.proxies)
            added = after - before
            self.total_fetched += added
            # Save to file
            with open(PROXY_FILE, 'w') as f:
                for p in sorted(self.proxies):
                    f.write(p + '\n')
        print(f"[PROXY] Pool: {after} (+{added})")
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
                    self.refresh()
                except Exception as e:
                    print(f"[PROXY ERROR] {e}")
                time.sleep(REFRESH_INTERVAL)
        self.refresh_thread = threading.Thread(target=loop, daemon=True)
        self.refresh_thread.start()

    def stop_auto(self):
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=2)

    def get(self):
        with self.lock:
            if not self.proxies:
                return None
            return random.choice(list(self.proxies))

    def count(self):
        with self.lock:
            return len(self.proxies)

    def load(self):
        print("[PROXY] Initial load...")
        self._load_from_file()
        # If file empty, do a scrape
        if len(self.proxies) == 0:
            self.refresh()
        else:
            print(f"[PROXY] Loaded {len(self.proxies)} proxies from file")
            if STATE_SYNC:
                state.update_proxy_stats(len(self.proxies), self.running, self.total_fetched)
        return len(self.proxies)

# ─── Singleton instance ───
proxy_manager = ProxyManager()

if __name__ == "__main__":
    print("SCYTHE PROXY MANAGER v11.0 — Advanced Scraper")
    proxy_manager.load()
    proxy_manager.start_auto()
    try:
        while True:
            time.sleep(10)
            print(f"[PROXY] Pool: {proxy_manager.count()}")
    except KeyboardInterrupt:
        proxy_manager.stop_auto()
        print("[PROXY] Stopped")