"""Private folder inventory. Signed selections bind a file version to one holder/session."""
import importlib.util
import os
from pathlib import Path
from django.core import signing

_spec = importlib.util.spec_from_file_location('foliolet_local_files',
    Path(__file__).resolve().parents[2] / 'tools/local-watcher/local_files.py')
_files = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_files)
SALT = 'foliolet-current-folder-file-v1'


def root_for(session):
    root = Path(session['folder'])
    if (not root.is_absolute() or len(root.parts) < 4 or not root.is_dir()
            or root.name.lower() in ('downloads', 'desktop', 'documents', 'users', 'windows', 'system32')):
        raise ValueError('The paired folder is unavailable.')
    for parent in (root, *root.parents):
        info = parent.lstat()
        if parent.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('The paired folder cannot contain a symlink or junction.')
    return root


def version(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def inventory(session, holder):
    root = root_for(session)
    rows = []
    for folder, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if not name.startswith('.')
            and not Path(folder, name).is_symlink()
            and not getattr(Path(folder, name).lstat(), 'st_file_attributes', 0) & (0x400 | 0x2 | 0x4)]
        for filename in filenames:
            try:
                path, relative = _files.safe_path(root, Path(folder, filename))
                info = path.stat()
                if not 0 < info.st_size <= _files.MAX_BYTES or len(path.name) > 150:
                    continue
                selection = {'session': session['id'], 'holder': holder, 'relative': relative, 'version': version(info)}
                rows.append({'selection': signing.dumps(selection, salt=SALT, compress=True),
                    'name': path.name, 'relativePath': relative, 'size': info.st_size,
                    'modifiedAt': info.st_mtime_ns // 1_000_000})
            except (OSError, ValueError):
                continue
    rows.sort(key=lambda row: (-row['modifiedAt'], row['relativePath'].casefold()))
    return rows


def read_selection(token, session, holder):
    selected = signing.loads(token, salt=SALT, max_age=3600)
    if selected.get('holder') != holder or selected.get('session') != session['id']:
        raise ValueError('The watcher pairing changed. Select a file from the updated list.')
    root = root_for(session)
    path, relative = _files.safe_path(root, root / selected['relative'])
    if version(path.stat()) != selected['version']:
        raise ValueError('This file changed. Select its updated row and retry.')
    relative, content = _files.stable_bytes(root, path, delay=0.15)
    if version(path.stat()) != selected['version']:
        raise ValueError('This file changed during import. Wait for the download to finish.')
    return relative, path.name, content
