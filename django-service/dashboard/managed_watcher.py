"""Private Docker control volume. The browser never receives the companion secret."""
import json
import os
from pathlib import Path
import uuid
from django.conf import settings

def enqueue(config):
    session = str(uuid.UUID(config['sessionId']))
    root = Path(settings.FOLIOLET_PAIRING_DIR)
    if root.is_symlink() or not root.is_dir() or len(list(root.glob('*.json'))) >= 64:
        raise ValueError('Watcher queue is unavailable; retry or use manual upload.')
    payload = json.dumps(config).encode('utf8')
    if len(payload) > 16384:
        raise ValueError('Pairing exceeds the local limit.')
    pending = root / ('.' + str(uuid.uuid4()) + '.pending')
    created = False
    try:
        fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(fd, 'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(pending, root / (session + '.json'))
    finally:
        if created:
            pending.unlink(missing_ok=True)
