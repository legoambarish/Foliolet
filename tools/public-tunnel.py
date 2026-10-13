"""Explicit opt-in manager. Never exposes the private Django/Spring processes."""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
import requests

def should_run(count, opted_in, tool_exists):
    return opted_in and tool_exists and count > 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--opt-in-exposure', action='store_true', help='Explicitly permit Cloudflare to handle disclosed packages')
    parser.add_argument('--named-tunnel', default='')
    parser.add_argument('--poll-seconds', type=int, default=10)
    args = parser.parse_args()
    binary = shutil.which('cloudflared')
    if not args.opt_in_exposure:
        raise SystemExit('Disabled: public exposure requires --opt-in-exposure. No process started.')
    if not binary:
        raise SystemExit('Disabled: cloudflared is unavailable. No process started.')
    username = os.environ.get('TUNNEL_OPERATOR_USER', 'governance')
    password = os.environ.get('TUNNEL_OPERATOR_PASSWORD', 'Foliolet-Demo-2026!')
    root = Path(__file__).resolve().parent.parent
    logs = root / '.bridge-data' / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    child = None
    try:
        with (logs / 'public-tunnel.log').open('a', encoding='utf-8') as log:
            while True:
                try:
                    response = requests.get('http://127.0.0.1:8080/api/bridge/demo/live-grants', auth=(username, password), timeout=5)
                    response.raise_for_status()
                    count = response.json()['count']
                except (requests.RequestException, ValueError, KeyError):
                    count = 0  # Fail closed when private service status is unavailable.
                if should_run(count, args.opt_in_exposure, bool(binary)) and child is None:
                    command = [binary, 'tunnel', '--no-autoupdate']
                    command += ['run', args.named_tunnel] if args.named_tunnel else ['--url', 'http://127.0.0.1:8001']
                    child = subprocess.Popen(command, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    print(json.dumps({'state': 'STARTED', 'activeGrants': count, 'port': 8001}), flush=True)
                if child and (not count or child.poll() is not None):
                    if child.poll() is None:
                        child.terminate()
                        child.wait(timeout=10)
                    child = None
                    print(json.dumps({'state': 'STOPPED', 'activeGrants': count}), flush=True)
                time.sleep(max(2, min(args.poll_seconds, 30)))
    finally:
        if child and child.poll() is None:
            child.terminate()
            child.wait(timeout=10)

if __name__ == '__main__':
    main()
