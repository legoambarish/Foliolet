"""Compose readiness includes actual services, local model and watcher supervisor."""
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from model import ready


def check():
    status = json.loads(Path('/app/.local-data/container-ready.json').read_text())
    for pid in status['pids']:
        os.kill(pid, 0)
    http = build_opener(ProxyHandler({}))
    with http.open('http://127.0.0.1:8000/login/', timeout=3) as response:
        if response.status != 200: raise ValueError('Private UI unavailable')
    try:
        http.open('http://127.0.0.1:8088/api/wallet/documents', timeout=3)
        raise ValueError('Private API unexpectedly accepted an unauthenticated request')
    except HTTPError as exc:
        if exc.code != 401: raise
    with http.open(Request('http://127.0.0.1:8548',
            data=b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}',
            headers={'Content-Type': 'application/json'}), timeout=3) as response:
        if json.load(response).get('result') != '0x539': raise ValueError('Wrong EVM chain')
    if not ready(status['model']): raise ValueError('Local model missing')


if __name__ == '__main__':
    try: check()
    except Exception:
        print('Foliolet is starting or a required service is unavailable.')
        sys.exit(1)
