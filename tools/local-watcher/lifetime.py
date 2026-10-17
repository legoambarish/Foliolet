"""Linux process identity used by container-managed, indefinite companions."""
from pathlib import Path


class LinuxAppLifetime:
    def __init__(self, pids, proc=Path('/proc')):
        if not pids or any(pid <= 0 for pid in pids):
            raise ValueError('The watcher needs its running Foliolet supervisor')
        self.proc = Path(proc)
        self.identities = {pid: self.identity(pid) for pid in pids}
        if not all(self.identities.values()):
            raise ValueError('Foliolet stopped before the watcher connected')

    def identity(self, pid):
        try:
            # comm can contain spaces and parentheses. Fields after the last ') '
            # start with state (field 3); starttime is field 22.
            fields = (self.proc / str(pid) / 'stat').read_text().rpartition(') ')[2].split()
            if fields[0] in ('Z', 'X', 'x'):
                return None
            return fields[19]
        except (OSError, IndexError):
            return None

    def active(self):
        return all(self.identity(pid) == identity for pid, identity in self.identities.items())

    def close(self):
        self.identities.clear()
