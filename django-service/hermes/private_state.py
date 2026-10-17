"""Local private state, without replacing or silently regenerating existing keys."""
import os
from pathlib import Path
import secrets
import stat


def load_secret(path: Path, configured: str | None = None) -> str:
    path = Path(path).absolute()
    directory = path.parent
    if directory.is_symlink() or getattr(directory, 'is_junction', lambda: False)():
        raise OSError('Private Django state cannot be a symlink or junction')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == 'posix': directory.chmod(0o700)
    if configured:
        return configured  # Explicit administrator-provided secret; never written here.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(secrets.token_urlsafe(48).encode('ascii'))
            handle.flush()
            os.fsync(handle.fileno())
    if path.is_symlink():
        raise OSError('The Django key must be a regular local file')
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise OSError('The Django key must be a regular local file')
        if os.name == 'posix': os.fchmod(handle.fileno(), 0o600)
        raw = handle.read(4097)
    if not 32 <= len(raw) <= 4096:
        raise ValueError('Existing Django key is invalid; restore it, do not generate a replacement')
    return raw.decode('utf-8')
