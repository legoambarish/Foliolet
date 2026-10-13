import argparse, json, time
import requests
parser = argparse.ArgumentParser()
parser.add_argument('model')
args = parser.parse_args()
last = 0
with requests.post('http://127.0.0.1:11434/api/pull', json={'model': args.model, 'stream': True}, stream=True, timeout=(10, 1800)) as response:
    response.raise_for_status()
    for line in response.iter_lines():
        if not line:
            continue
        event = json.loads(line)
        if 'error' in event:
            raise SystemExit(event['error'])
        now = time.monotonic()
        if now-last > 20 or event.get('status') == 'success':
            print(json.dumps({'model': args.model, **event}), flush=True)
            last = now
