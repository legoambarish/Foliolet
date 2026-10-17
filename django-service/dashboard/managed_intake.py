"""Private per-holder capabilities for the opt-in container watcher supervisor."""
import hashlib
import json
import os
from pathlib import Path
import re
import uuid


def validate(config, folder):
    if not isinstance(config, dict): raise ValueError('Invalid managed watcher pairing')
    if (config.get('folder') != str(folder) or config.get('apiUrl') != 'http://127.0.0.1:8088'
            or config.get('folderHash') != hashlib.sha256(str(folder).encode()).hexdigest()
            or not re.fullmatch(r'[0-9a-f-]{36}', config.get('sessionId', ''))
            or not re.fullmatch(r'[0-9a-f]{64}', config.get('token', ''))
            or config.get('lifetime') != 'app' or config.get('expiresAt') is not None
            or not config.get('agentId') or not config.get('secret')):
        raise ValueError('Invalid managed watcher pairing')
    uuid.UUID(config['sessionId'])
    return config


def save(config, holder, directory, folder):
    validate(config, folder)
    directory = Path(directory)
    if directory.is_symlink(): raise ValueError('Watcher state cannot be a symlink')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    slot = hashlib.sha256(holder.encode()).hexdigest()
    target = directory / (slot + '.json')
    temporary = directory / (slot + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            if os.name == 'posix': os.fchmod(stream.fileno(), 0o600)
            json.dump(config, stream); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
