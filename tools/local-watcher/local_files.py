"""Safe, stable local-file reads shared by the companion and private UI."""
import os
import stat
import time
from pathlib import Path

MAX_BYTES = 20 * 1024 * 1024
SUFFIXES = {".pdf", ".txt", ".csv"}


def safe_path(root, incoming):
    root, path = Path(os.path.abspath(root)), Path(os.path.abspath(incoming))
    relative = path.relative_to(root)
    if not relative.parts or any(p.startswith('.') or ':' in p for p in relative.parts):
        raise ValueError('Hidden or external path')
    for current in (path, *path.parents):
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Symlinks and junctions are not eligible')
        if current == root:
            # Root ancestors are also checked, so the allowed root cannot itself escape.
            for parent in root.parents:
                pinfo = parent.lstat()
                if stat.S_ISLNK(pinfo.st_mode) or getattr(pinfo, 'st_file_attributes', 0) & 0x400:
                    raise ValueError('The folder has a reparse-point ancestor')
            break
    if path.suffix.lower() not in SUFFIXES or not path.is_file():
        raise ValueError('Use a completed supported file')
    attrs = getattr(path.stat(), 'st_file_attributes', 0)
    if attrs & (0x2 | 0x4):
        raise ValueError('Hidden/system file')
    return path, relative.as_posix()


def open_stable_handle(path):
    if os.name == 'nt':
        import ctypes
        import msvcrt
        from ctypes import wintypes
        create = ctypes.WinDLL('kernel32', use_last_error=True).CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        # Permit concurrent readers, deny all writers and deletion/rename while reading.
        handle = create(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise OSError('File is locked or unavailable')
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except Exception:
            ctypes.windll.kernel32.CloseHandle(handle)
            raise
        return os.fdopen(fd, 'rb')
    return os.fdopen(os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)), 'rb')


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def stable_bytes(root, incoming, delay=1.0):
    path, relative = safe_path(root, incoming)
    before = path.stat()
    if not 0 < before.st_size <= MAX_BYTES:
        raise ValueError('Empty or oversized file')
    time.sleep(delay)
    if identity(path.stat()) != identity(before):
        raise OSError('File is still changing')
    with open_stable_handle(path) as source:
        held = os.fstat(source.fileno())
        if identity(held) != identity(before):
            raise OSError('File changed before opening')
        content = source.read(MAX_BYTES + 1)
        time.sleep(delay)
        after, _ = safe_path(root, path)
        if (len(content) != held.st_size or identity(os.fstat(source.fileno())) != identity(held)
                or identity(after.stat()) != identity(held)):
            raise OSError('File changed while reading')
    if path.suffix.lower() == '.pdf' and (not content.startswith(b'%PDF-') or b'%%EOF' not in content[-2048:]):
        raise OSError('PDF download is incomplete')
    return relative, content
