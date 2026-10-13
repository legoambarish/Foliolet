"""Narrow reproducible source scan. Does not read ignored private vaults or legacy secrets."""
import re, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
new=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
patterns=[re.compile(r'(?<![\w-])sk-(?:proj-)?[A-Za-z0-9_-]{30,}'),re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}')]
hits=[];scanned=0
for name in sorted(set(tracked+new)):
    if not name or name.startswith('output/') or name=='docs/EVOLUTION_FROM_EVIDENTIA.md':continue
    file=root/name
    if not file.is_file() or file.stat().st_size>3_000_000:continue
    try:text=file.read_text(encoding='utf-8')
    except (UnicodeError,OSError):continue
    scanned+=1
    for number,line in enumerate(text.splitlines(),1):
        if any(pattern.search(line) for pattern in patterns):hits.append(f'{name}:{number}')
print({'files_scanned':scanned,'suspected_secret_locations':hits,'scope':'tracked and implementation source; ignored private data excluded'})
sys.exit(bool(hits))
