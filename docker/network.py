"""Hold the private namespace independently of framework/model process restarts."""
import signal
import threading

stopped = threading.Event()
for signum in (signal.SIGTERM, signal.SIGINT):
    signal.signal(signum, lambda *_: stopped.set())
stopped.wait()
