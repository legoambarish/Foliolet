"""Initialize only dedicated Docker volumes; retained state is never replaced."""
import os
from pathlib import Path
import secrets

def initialize():
    for folder in ('/app/.local-data', '/pairings', '/watcher-state', '/run/foliolet-secrets'):
        path = Path(folder)
        path.mkdir(exist_ok=True, parents=True, mode=0o700)
        os.chown(path, 1000, 1000)
        path.chmod(0o700)
    path = Path('/run/foliolet-secrets/postgres-password')
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write(secrets.token_urlsafe(40))
    if path.is_symlink() or not 32 <= len(path.read_text().strip()) <= 200:
        raise RuntimeError('Restore the retained Docker database secret; it was not replaced.')
    os.chown(path, 1000, 1000)
    print('Dedicated Docker state and retained database secret ready.', flush=True)

if __name__ == '__main__': initialize()
