"""Generate only missing Compose secrets. Never replace retained identities."""
import os
from pathlib import Path
import re
import secrets


def initialize(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    password = directory / 'postgres-password'
    try:
        fd = os.open(password, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError:
        if password.is_symlink() or not re.fullmatch(r'[0-9a-f]{64}', password.read_text()):
            raise ValueError('Retained database secret is invalid; restore it instead of replacing it')
    else:
        with os.fdopen(fd, 'w') as stream:
            stream.write(secrets.token_hex(32))
            stream.flush(); os.fsync(stream.fileno())
        # Both PostgreSQL and app UIDs read this file from read-only mounts.
        password.chmod(0o444)


if __name__ == '__main__':
    initialize('/run/foliolet')
    print('[setup] Persistent database secret ready; no .env file needed.', flush=True)
