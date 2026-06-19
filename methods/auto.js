// SCYTHE <METHOD> v6.0 — REAL Attack (delegates to Python engine)
const { execSync } = require('child_process');

// Usage: node <method>.js <target> <time> <rate> <threads> [proxyFile]
execSync(`python3 methods/l7_engine.py <method> "<target>" <time> <threads> <proxyFile>`, {
    encoding: 'utf-8',
    stdio: 'inherit',
    timeout: (parseInt(time) + 10) * 1000
});