"""One receiver/tunnel owner per checkout, with bounded authenticated local control.

No Django worker owns children. A detached supervisor holds an OS file lock for
its lifetime. Client startup is serialized by a separate OS lock. No request
URL, backend error, bearer token, cookie or raw cloudflared output is logged.
"""
import contextlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import requests

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = Path(os.environ.get('FOLIOLET_STATE_DIR', ROOT / '.local-data')) / 'receiver'
QUICK_HOST = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com")
TOKEN_PATH = re.compile(r"/verify/[0-9a-f]{64}/")


class TunnelError(Exception):
    """Only curated, non-sensitive messages may be passed to this exception."""


def validate_origin(value, *, quick=True):
    if not isinstance(value, str) or len(value) > 253:
        raise TunnelError("Invalid public HTTPS origin.")
    try:
        url = urlsplit(value)
        host = url.hostname or ""
        if (url.scheme != "https" or url.port is not None or url.username or url.password
                or url.path or url.query or url.fragment or url.netloc != host
                or value != "https://" + host):
            raise ValueError
        if quick:
            if not QUICK_HOST.fullmatch(host):
                raise ValueError
        else:
            if (not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
                                r"[a-z]{2,63}", host)
                    or host.endswith((".localhost", ".local", ".internal", ".test"))):
                raise ValueError
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                raise ValueError
    except ValueError:
        raise TunnelError("Invalid public HTTPS origin.") from None
    return value


def share_path(value):
    """Accept only the exact internal Spring verification route, never a redirect."""
    if not isinstance(value, str):
        raise TunnelError("The document service returned an invalid share link.")
    try:
        url = urlsplit(value)
        expected = urlsplit(os.environ.get("WALLET_SHARE_BASE_URL", "http://localhost:8000"))
    except ValueError:
        raise TunnelError("The document service returned an invalid share link.") from None
    allowed = {(expected.scheme, expected.netloc), ("http", "localhost:8000"),
               ("http", "127.0.0.1:8000")}
    named = os.environ.get("FOLIOLET_PUBLIC_BASE_URL", "")
    if named:
        allowed.add(("https", urlsplit(validate_origin(named, quick=False)).netloc))
    if ((url.scheme, url.netloc) not in allowed or url.username or url.password
            or url.query or url.fragment or not TOKEN_PATH.fullmatch(url.path)):
        raise TunnelError("The document service returned an invalid share link.")
    return url.path


def config():
    mode = os.environ.get("FOLIOLET_SHARE_MODE", "quick")
    if mode not in ("quick", "named", "local"):
        raise TunnelError("FOLIOLET_SHARE_MODE must be quick, named or local.")
    try:
        port = int(os.environ.get("FOLIOLET_RECEIVER_PORT", "8001"))
        control = int(os.environ.get("FOLIOLET_CONTROL_PORT", "8002"))
        timeout = int(os.environ.get("FOLIOLET_TUNNEL_TIMEOUT", "60"))
        if (not 1024 <= port <= 65535 or not 1024 <= control <= 65535
                or port == control or port in (8000, 8080, 8545, 5432, 55432, 55433)
                or control in (8000, 8080, 8545, 5432, 55432, 55433)
                or not 10 <= timeout <= 60):
            raise ValueError
    except ValueError:
        raise TunnelError("Invalid dedicated receiver/control port or startup timeout.") from None
    return {"mode": mode, "port": port, "control": control, "timeout": timeout}


@contextlib.contextmanager
def file_lock(name, timeout):
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE_DIR / name).open("a+b") as handle:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TunnelError("Another share startup is busy; retry shortly.") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def control_key():
    path = STATE_DIR / "control.key"
    if not path.exists():
        try:
            with path.open("x", encoding="ascii") as output:
                output.write(secrets.token_hex(32))
            path.chmod(0o600)
        except FileExistsError:
            pass
    key = path.read_text(encoding="ascii")
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        raise TunnelError("Restore the local receiver control key; do not use a partial key.")
    return key


def rpc(action, cfg, timeout=3):
    session = requests.Session()
    session.trust_env = False  # Local control must never go through an HTTP proxy.
    try:
        response = session.post("http://127.0.0.1:%d/%s" % (cfg["control"], action),
                                headers={"Authorization": "Bearer " + control_key()},
                                timeout=(1, timeout), allow_redirects=False)
        if response.status_code not in (200, 503):
            raise TunnelError("The local control port is occupied by another service.")
        value = response.json()
        if not isinstance(value, dict) or value.get("workspace") != str(ROOT):
            raise TunnelError("The receiver belongs to a different checkout.")
        if response.status_code != 200:
            raise TunnelError(value.get("error", "Public receiver is unavailable."))
        return value
    except (requests.RequestException, ValueError):
        raise TunnelError("The local tunnel supervisor is not responding.") from None
    finally:
        session.close()


def ensure_public():
    cfg = config()
    if cfg["mode"] == "local":
        return {"mode": "local", "origin": "", "state": "local"}
    with file_lock("client.lock", cfg["timeout"] + 5):
        control_key()
        try:
            current = rpc("status", cfg)
        except TunnelError:
            # The supervisor's lifetime lock prevents duplicate owners even if
            # two app processes race or a stale control port is occupied.
            kwargs = {"cwd": ROOT, "stdin": subprocess.DEVNULL,
                      "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if os.name == "nt":
                kwargs["creationflags"] = (subprocess.DETACHED_PROCESS |
                                           subprocess.CREATE_NEW_PROCESS_GROUP |
                                           subprocess.CREATE_NO_WINDOW)
            else:
                kwargs["start_new_session"] = True
            subprocess.Popen([sys.executable, str(ROOT / "tools" / "share-tunnel.py"), "serve"], **kwargs)
            deadline = time.monotonic() + 8
            while True:
                try:
                    current = rpc("status", cfg, timeout=1)
                    break
                except TunnelError:
                    if time.monotonic() >= deadline:
                        raise TunnelError("Could not start the local supervisor. Check ports/dependencies and run share-tunnel.py start.") from None
                    time.sleep(0.1)
        if current.get("mode") != cfg["mode"]:
            raise TunnelError("Sharing mode changed. Stop the existing supervisor before starting this mode.")
        return rpc("ensure", cfg, timeout=cfg["timeout"] + 5)


def confirm_public(snapshot):
    if snapshot["mode"] == "local":
        return
    current = rpc("check", config(), timeout=7)
    if (current.get("origin") != snapshot.get("origin")
            or current.get("instance") != snapshot.get("instance")):
        raise TunnelError("The tunnel restarted during share creation. This link was not published.")


def cloudflared_binary():
    path = os.environ.get("CLOUDFLARED_PATH") or shutil.which("cloudflared")
    if not path:
        path = ROOT / ".local-tools" / "cloudflared" / ("cloudflared.exe" if os.name == "nt" else "cloudflared")
    if not Path(path).is_file():
        raise TunnelError("Install official cloudflared or set CLOUDFLARED_PATH, then retry. No share was created.")
    try:
        version = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=5)
        if version.returncode or not re.search(r"cloudflared version \d{4}\.\d+\.\d+", version.stdout):
            raise ValueError
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raise TunnelError("The configured cloudflared executable is unavailable or unsupported.") from None
    return str(Path(path).resolve())


def windows_child_job(child):
    """Kill cloudflared if its supervisor exits abruptly, including Task Manager."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes as W
    class Limits(ctypes.Structure):
        _fields_ = [("time1", ctypes.c_int64), ("time2", ctypes.c_int64), ("flags", W.DWORD),
                    ("min", ctypes.c_size_t), ("max", ctypes.c_size_t), ("active", W.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", W.DWORD), ("scheduling", W.DWORD)]
    class Extended(ctypes.Structure):
        _fields_ = [("basic", Limits), ("io", ctypes.c_uint64 * 6),
                    ("memory", ctypes.c_size_t * 4)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = W.HANDLE
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, W.LPCWSTR]
    kernel.SetInformationJobObject.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job, W.HANDLE(int(child._handle))):
        if job:
            kernel.CloseHandle(job)
        child.terminate()
        child.wait(timeout=5)
        raise TunnelError("Could not establish safe tunnel process ownership.")
    return lambda: kernel.CloseHandle(job)


class Supervisor:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.child = self.job_close = self.origin_server = None
        self.origin_thread = None
        self.origin = ""
        self.instance = secrets.token_hex(16)
        self.state = "stopped"
        self.error = ""
        self.last_origin = ""
        self.connection = "waiting"
        self.health_status = "unchecked"
        self.health_error = ""
        self.url_seen_at = 0

    def status(self):
        state = self.state
        if state == "ready" and self.child and self.child.poll() is not None:
            state = "unavailable"
        return {"workspace": str(ROOT), "state": state, "mode": self.cfg["mode"],
                "origin": self.origin if state == "ready" else "", "instance": self.instance,
                "supervisorPid": os.getpid(), "tunnelPid": self.child.pid if self.child and self.child.poll() is None else None,
                "error": self.error, "lastOrigin": self.last_origin,
                "connection": self.connection, "healthStatus": self.health_status,
                "healthError": self.health_error}

    def healthy(self):
        if not self.origin or (self.child and self.child.poll() is not None):
            return False
        try:
            response = requests.get(self.origin + "/healthz/", timeout=(2, 3),
                                    allow_redirects=False, headers={"Cache-Control": "no-cache"})
            self.health_status = response.status_code
            self.health_error = ""
            return response.status_code == 200 and response.json() == {
                "service": "foliolet-receiver", "instance": self.instance}
        except (requests.RequestException, ValueError) as exc:
            self.health_status = "network-unavailable"
            self.health_error = type(exc).__name__
            return False

    def start_origin(self):
        if self.origin_server:
            return
        os.environ["DJANGO_SETTINGS_MODULE"] = "hermes.receiver_settings"
        os.environ["FOLIOLET_RECEIVER_INSTANCE"] = self.instance
        from django.core.wsgi import get_wsgi_application
        from django.core.management import call_command
        from django.db import connections
        from waitress import create_server
        app = get_wsgi_application()
        call_command("migrate", interactive=False, verbosity=0)
        connections.close_all()
        self.origin_server = create_server(app, host="127.0.0.1", port=self.cfg["port"],
            threads=8, connection_limit=64, channel_timeout=30, cleanup_interval=5,
            max_request_body_size=16384, max_request_header_size=8192,
            expose_tracebacks=False, trusted_proxy="127.0.0.1",
            trusted_proxy_headers={"x-forwarded-proto"}, clear_untrusted_proxy_headers=True,
            ident="Foliolet receiver")
        self.origin_thread = threading.Thread(target=self.origin_server.run, daemon=True)
        self.origin_thread.start()

    def read_output(self, child):
        for line in child.stdout:
            # Never persist raw log lines. INFO is necessary for the initial URL;
            # debug (which includes requests/headers) is never enabled.
            if child is self.child and "Registered tunnel connection" in line:
                self.connection = "registered"
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com(?=\s|$)", line)
            if match and child is self.child:
                try:
                    origin = validate_origin(match.group())
                except TunnelError:
                    continue
                from django.conf import settings
                self.origin = origin
                self.last_origin = origin
                self.url_seen_at = time.monotonic()
                settings.PUBLIC_RECEIVER_ORIGIN = origin

    def start_tunnel(self):
        binary = cloudflared_binary()
        # Explicit empty config bypasses discovery of user credentials/config;
        # never rename/delete ~/.cloudflared files. It is not a named tunnel.
        isolated = STATE_DIR / "quick.yml"
        isolated.write_text("{}\n", encoding="ascii")
        env = {k: v for k, v in os.environ.items()
               if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "HOME",
                                 "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SSL_CERT_FILE", "SSL_CERT_DIR"}}
        args = [binary, "tunnel", "--config", str(isolated), "--no-autoupdate",
                "--protocol", "http2",
                "--metrics", "127.0.0.1:0", "--loglevel", "info",
                "--management-diagnostics=false", "--url", "http://127.0.0.1:%d" % self.cfg["port"],
                "--no-chunked-encoding"]
        kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
                  "stdin": subprocess.DEVNULL, "text": True, "encoding": "utf-8",
                  "errors": "replace", "cwd": STATE_DIR, "env": env}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        self.child = subprocess.Popen(args, **kwargs)
        self.job_close = windows_child_job(self.child)
        threading.Thread(target=self.read_output, args=(self.child,), daemon=True).start()

    def stop_tunnel(self):
        if self.child:
            if self.child.poll() is None:
                self.child.terminate()
                try:
                    self.child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.child.kill()
                    self.child.wait(timeout=5)
            if self.job_close:
                self.job_close()
            self.child = self.job_close = None
        self.origin = ""
        if self.origin_server:
            from django.conf import settings
            settings.PUBLIC_RECEIVER_ORIGIN = ""

    def ensure(self):
        with self.lock:
            if self.stop_event.is_set():
                raise TunnelError("The supervisor is stopping; retry after it stops.")
            if self.state == "ready" and self.healthy():
                return self.status()
            if self.child and self.child.poll() is None:
                raise TunnelError("The active tunnel is unavailable. Retry or explicitly restart; no new share was created.")
            self.stop_tunnel()
            self.state, self.error = "starting", ""
            deadline = time.monotonic() + self.cfg["timeout"]
            try:
                self.start_origin()
                if self.cfg["mode"] == "quick":
                    self.start_tunnel()
                else:
                    from django.conf import settings
                    self.origin = validate_origin(os.environ.get("FOLIOLET_PUBLIC_BASE_URL", ""), quick=False)
                    settings.PUBLIC_RECEIVER_ORIGIN = self.origin
                while time.monotonic() < deadline:
                    if self.stop_event.is_set():
                        raise TunnelError("Tunnel startup was stopped.")
                    if self.child and self.child.poll() is not None:
                        raise TunnelError("cloudflared exited before becoming ready. Check connectivity or run the official CLI locally.")
                    # Quick Tunnel DNS/routing may lag the printed URL. Avoid an
                    # immediate lookup which can poison Windows' negative cache.
                    if (self.cfg["mode"] != "quick" or time.monotonic() - self.url_seen_at >= 3) and self.healthy():
                        self.state = "ready"
                        return self.status()
                    self.stop_event.wait(0.25)
                raise TunnelError("Public HTTPS readiness timed out. No public share was created; check Internet/tunnel routing and retry.")
            except Exception as exc:
                self.state = "unavailable"
                self.error = str(exc) if isinstance(exc, TunnelError) else "Receiver startup failed. Check local ports/dependencies."
                self.stop_tunnel()
                raise TunnelError(self.error) from None

    def check(self):
        with self.lock:
            if self.state != "ready" or not self.healthy():
                raise TunnelError("Public receiver health failed; this share cannot be published.")
            return self.status()

    def close(self):
        self.stop_event.set()
        with self.lock:
            self.stop_tunnel()
            if self.origin_server:
                self.origin_server.task_dispatcher.shutdown(cancel_pending=True, timeout=3)
                self.origin_server.close()
            self.state = "stopped"


def serve():
    cfg = config()
    with file_lock("supervisor.lock", 0):
        owner = Supervisor(cfg)
        key = control_key()
        class Control(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if (self.headers.get("Origin") or self.headers.get("Host") != "127.0.0.1:%d" % cfg["control"]
                        or not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + key)
                        or self.headers.get("Content-Length", "0") != "0"
                        or self.headers.get("Transfer-Encoding")):
                    self.send_error(403)
                    return
                try:
                    if self.path == "/ensure":
                        value = owner.ensure()
                    elif self.path == "/check":
                        value = owner.check()
                    elif self.path == "/status":
                        value = owner.status()
                    elif self.path == "/stop":
                        owner.stop_event.set()
                        value = owner.status()
                    else:
                        self.send_error(404)
                        return
                    code = 200
                except TunnelError as exc:
                    code, value = 503, owner.status() | {"error": str(exc)}
                data = json.dumps(value).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        server = None
        try:
            server = ThreadingHTTPServer(("127.0.0.1", cfg["control"]), Control)
            server.timeout = 0.5
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda *_: owner.stop_event.set())
            while not owner.stop_event.is_set():
                server.handle_request()
        finally:
            if server:
                server.server_close()
            owner.close()


def stop_public():
    cfg = config()
    with file_lock("client.lock", cfg["timeout"] + 5):
        rpc("stop", cfg)
        deadline = time.monotonic() + cfg["timeout"] + 10
        while time.monotonic() < deadline:
            try:
                rpc("status", cfg, timeout=1)
            except TunnelError:
                return
            time.sleep(0.1)
        raise TunnelError("Supervisor shutdown has not completed. Inspect local processes before restarting.")
