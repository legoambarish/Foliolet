"""Package the current public source, including local fixes, for transfer to a Mac."""
import hashlib
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.local-data/Foliolet-macos-source.zip'
EXCLUDED = {'.git', '.local-data', '.local-tools', '.venv', 'venv', 'node_modules',
            'target', '__pycache__', 'uploaded-documents', 'document-backups', 'output'}
PRIVATE = {'.key', '.pem', '.p12', '.pfx', '.jks', '.sqlite', '.sqlite3', '.db', '.pyc'}


def public(path):
    name = path.name.lower()
    return not (set(path.parts) & EXCLUDED or path.suffix.lower() in PRIVATE
        or (name.startswith('.env') and name != '.env.example')
        or name == '.ds_store' or name.endswith('.log')
        or (name.endswith('.json') and ('pairing' in name or name.startswith('foliolet-intake')))
        or path.as_posix().startswith('docs/screenshots/')
        or path.as_posix() in ('spring-boot-service/src/main/resources/application.properties',
                               'spring-boot-service/src/main/resources/application.yaml'))


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    files = sorted({Path(value.decode('utf-8')) for value in paths.split(b'\0') if value})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        def write(name, content):
            info = zipfile.ZipInfo('Foliolet/' + name)
            info.create_system = 3
            mode = 0o755 if name.endswith('.sh') or Path(name).name == 'mvnw' else 0o644
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
        for relative in files:
            file = ROOT / relative
            if not public(relative) or not file.is_file():
                continue
            if any(parent.is_symlink() or getattr(parent.lstat(), 'st_file_attributes', 0) & 0x400
                   for parent in (file, *file.parents) if parent != ROOT.parent):
                raise ValueError('Source package cannot follow a symlink or junction')
            content = file.read_bytes()
            write(relative.as_posix(), content)
            manifest.append(hashlib.sha256(content).hexdigest() + '  ' + relative.as_posix())
        write('SOURCE-SHA256SUMS', '\n'.join(manifest) + '\n')
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_suffix('.zip.sha256').write_text(digest + '  ' + OUTPUT.name + '\n')
    print(str(OUTPUT))
    print(str(len(manifest)) + ' source files; ' + str(OUTPUT.stat().st_size) + ' bytes')
    print('SHA-256: ' + digest)


if __name__ == '__main__':
    main()
