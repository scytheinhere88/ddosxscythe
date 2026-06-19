#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCYTHE STATE MANAGER v10.0 — AUTO TOTAL RPS + FULL SYNC
"""
import os
import json
import time
import threading
import uuid

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

MAX_CONCURRENT = 5
MAX_HOLD_TIME = 86400

class StateManager:
    def __init__(self, filepath='state.json'):
        self.filepath = filepath
        self._thread_lock = threading.Lock()
        self._ensure_defaults()

    def _ensure_defaults(self):
        defaults = {
            'active_attacks': [],
            'attack_history': [],
            'method_stats': {},
            'total_rps': 0,
            'total_requests': 0,
            'total_bytes': 0,
            'proxy_pool': 0,
            'proxy_total_fetched': 0,
            'proxy_refreshing': False,
            'system_status': 'online',
            'system_resources': {'cpu': 0, 'memory': 0, 'disk': 0, 'network': 0},
            'last_updated': time.time(),
            'max_concurrent': MAX_CONCURRENT,
        }
        loaded = self._load_file()
        if loaded is None:
            self.state = defaults
            self._save_file()
        else:
            for k, v in defaults.items():
                if k not in loaded:
                    loaded[k] = v
            self.state = loaded
            self._save_file()

    def _load_file(self):
        if not os.path.exists(self.filepath):
            return None
        try:
            with open(self.filepath, 'r') as f:
                if FCNTL_AVAILABLE:
                    fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    if FCNTL_AVAILABLE:
                        fcntl.flock(f, fcntl.LOCK_UN)
        except:
            return None

    def _save_file(self):
        try:
            tmp = self.filepath + '.tmp'
            with open(tmp, 'w') as f:
                if FCNTL_AVAILABLE:
                    fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    json.dump(self.state, f, indent=2)
                finally:
                    if FCNTL_AVAILABLE:
                        fcntl.flock(f, fcntl.LOCK_UN)
            os.replace(tmp, self.filepath)
        except Exception as e:
            print(f"[STATE SAVE ERROR] {e}")

    def _reload(self):
        loaded = self._load_file()
        if loaded is not None:
            self.state = loaded

    # ─── 🔥 AUTO RECALCULATE TOTAL RPS ───
    def _recalculate_total_rps(self):
        """Jumlahkan rps dari semua attack aktif dan simpan ke state['total_rps']"""
        total = sum(atk.get('rps', 0) for atk in self.state.get('active_attacks', []))
        self.state['total_rps'] = total
        self.state['total_requests'] = sum(atk.get('total_requests', 0) for atk in self.state.get('active_attacks', []))
        self.state['total_bytes'] = sum(atk.get('total_bytes', 0) for atk in self.state.get('active_attacks', []))

    # ─── ATTACK MANAGEMENT ───
    def add_attack(self, target, method, duration, layer, proxy_count, hold_time, threads):
        with self._thread_lock:
            self._reload()
            if len(self.state['active_attacks']) >= MAX_CONCURRENT:
                return False, "Max concurrent attacks reached"
            attack_id = str(uuid.uuid4())[:16]
            attack = {
                'id': attack_id,
                'target': target,
                'method': method,
                'duration': int(duration),
                'layer': layer,
                'start_time': time.time(),
                'hold_time': int(hold_time),
                'proxy_count_initial': proxy_count,
                'proxy_count_current': proxy_count,
                'threads': threads,
                'rps': 0,
                'peak_rps': 0,
                'total_requests': 0,
                'total_bytes': 0,
                'status': 'running',
            }
            self.state['active_attacks'].append(attack)
            self._recalculate_total_rps()
            self._save_file()
            return True, attack_id

    def remove_attack(self, attack_id):
        with self._thread_lock:
            self._reload()
            active = self.state['active_attacks']
            for i, atk in enumerate(active):
                if atk['id'] == attack_id:
                    removed = active.pop(i)
                    removed['status'] = 'stopped'
                    removed['end_time'] = time.time()
                    self.state['attack_history'].append(removed)
                    if len(self.state['attack_history']) > 1000:
                        self.state['attack_history'] = self.state['attack_history'][-1000:]
                    self._update_method_stats(removed)
                    self._recalculate_total_rps()
                    self._save_file()
                    return True
            return False

    def update_rps(self, attack_id, rps, total_requests, peak_rps, proxy_count, total_bytes=0):
        with self._thread_lock:
            self._reload()
            for atk in self.state['active_attacks']:
                if atk['id'] == attack_id:
                    atk['rps'] = rps
                    atk['total_requests'] = total_requests
                    atk['peak_rps'] = max(atk['peak_rps'], peak_rps)
                    atk['proxy_count_current'] = proxy_count
                    if total_bytes > 0:
                        atk['total_bytes'] = total_bytes
                    self._recalculate_total_rps()
                    self._save_file()
                    return True
            return False

    def stop_all(self):
        with self._thread_lock:
            self._reload()
            for atk in self.state['active_attacks'][:]:
                atk['status'] = 'stopped'
                atk['end_time'] = time.time()
                self.state['attack_history'].append(atk)
                self._update_method_stats(atk)
            self.state['active_attacks'] = []
            if len(self.state['attack_history']) > 1000:
                self.state['attack_history'] = self.state['attack_history'][-1000:]
            self._recalculate_total_rps()
            self._save_file()

    # ─── PROXY STATS ───
    def update_proxy_stats(self, pool_count, refreshing, total_fetched):
        with self._thread_lock:
            self._reload()
            self.state['proxy_pool'] = pool_count
            self.state['proxy_refreshing'] = refreshing
            self.state['proxy_total_fetched'] = total_fetched
            self.state['last_updated'] = time.time()
            self._save_file()

    # ─── METHOD STATS ───
    def _update_method_stats(self, attack):
        method = attack.get('method', 'unknown')
        if method not in self.state['method_stats']:
            self.state['method_stats'][method] = {'uses': 0, 'total_requests': 0, 'peak_rps': 0, 'avg_rps': 0}
        stats = self.state['method_stats'][method]
        stats['uses'] += 1
        stats['total_requests'] += attack.get('total_requests', 0)
        stats['peak_rps'] = max(stats['peak_rps'], attack.get('peak_rps', 0))
        total_rps = attack.get('peak_rps', 0)
        if stats['uses'] > 1:
            stats['avg_rps'] = (stats['avg_rps'] * (stats['uses'] - 1) + total_rps) // stats['uses']
        else:
            stats['avg_rps'] = total_rps

    # ─── GET STATE ───
    def get_state(self):
        with self._thread_lock:
            self._reload()
            return self.state.copy()

    def _save(self):
        with self._thread_lock:
            self._save_file()

state = StateManager()