"""Download a pinned official portable runtime into isolated, ignored demo state."""
import hashlib
import time
import zipfile
from pathlib import Path
import requests
VERSION = '0.40.3'
NAME = 'ollama-windows-amd64.zip'
BASE = f'https://github.com/ollama/ollama/releases/download/v{VERSION}/'
root = Path(__file__).resolve().parent.parent / '.bridge-data/tools/ollama'
root.mkdir(parents=True, exist_ok=True)
archive = root.parent / NAME
# Published asset digest from the official GitHub release API, verified 13 October 2026.
expected = 'e5ecff02dfc7cae8ddf6d6b7a7ac5f727ffeedf4491f44ae75ff5b0820dbbbd5'
if not archive.exists():
    with requests.get(BASE + NAME, stream=True, timeout=(15, 60)) as response:
        response.raise_for_status()
        count = 0
        last = time.monotonic()
        with archive.with_suffix('.partial').open('wb') as output:
            for chunk in response.iter_content(1024 * 1024):
                output.write(chunk)
                count += len(chunk)
                if time.monotonic() - last > 20:
                    print(time.strftime('%H:%M:%S'), 'portable Ollama download', round(count / 1048576), 'MiB', flush=True)
                    last = time.monotonic()
        archive.with_suffix('.partial').rename(archive)
with archive.open('rb') as source:
    digest = hashlib.file_digest(source, 'sha256').hexdigest()
if digest != expected:
    raise RuntimeError('Official archive checksum mismatch; preserve file for investigation')
with zipfile.ZipFile(archive) as bundle:
    for entry in bundle.infolist():
        target = (root / entry.filename).resolve()
        if not target.is_relative_to(root.resolve()):
            raise RuntimeError('Archive path escapes runtime directory')
    bundle.extractall(root)
print('Portable Ollama verified and extracted:', root, flush=True)
