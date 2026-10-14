"""Restricted HTTPS receiver. Only the local tunnel supervisor starts this profile."""
from .settings import *  # noqa: F403

DEBUG = False
RECEIVER_ONLY = True
ENABLE_LEGACY_UI = False
ROOT_URLCONF = "hermes.receiver_urls"
# No admin or mail entry points exist on the receiver. Keep only the base apps
# needed by shared templates, sessions and disclosure views.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django.contrib.admin"]
MAILERS = {}
# An absent mailer is intentional; accidental mail sending must fail closed.
SILENCED_SYSTEM_CHECKS = ["mail.W001"]
ALLOWED_HOSTS = ["127.0.0.1", ".trycloudflare.com"]
PUBLIC_RECEIVER_ORIGIN = os.environ.get("FOLIOLET_PUBLIC_BASE_URL", "")
if PUBLIC_RECEIVER_ORIGIN:
    from dashboard.tunnel_manager import validate_origin
    from urllib.parse import urlsplit
    PUBLIC_RECEIVER_ORIGIN = validate_origin(PUBLIC_RECEIVER_ORIGIN, quick=False)
    ALLOWED_HOSTS.append(urlsplit(PUBLIC_RECEIVER_ORIGIN).hostname)
PUBLIC_RECEIVER_INSTANCE = os.environ.get("FOLIOLET_RECEIVER_INSTANCE", "")

# Separate storage, secret and cookie names prevent private holder sessions being
# accepted by the public application, even if somebody copies a session cookie.
_receiver_dir = BASE_DIR.parent / ".local-data" / "receiver"
_receiver_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
_receiver_key = _receiver_dir / "django.key"
if not _receiver_key.exists():
    try:
        with _receiver_key.open("x", encoding="utf-8") as key_file:
            key_file.write(secrets.token_urlsafe(48))
        _receiver_key.chmod(0o600)
    except FileExistsError:
        pass
SECRET_KEY = _receiver_key.read_text(encoding="utf-8")
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": _receiver_dir / "sessions.sqlite3"}}
SESSION_COOKIE_NAME = "__Host-foliolet-receiver"
CSRF_COOKIE_NAME = "__Host-foliolet-receiver-csrf"
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_TRUSTED_ORIGINS = []  # The exact HTTPS Host is also the form's Origin.
CSRF_FAILURE_VIEW = "dashboard.receiver_surface.csrf_failure"

# Waitress trusts X-Forwarded-Proto only from its loopback peer and sets the WSGI
# scheme. Do not independently trust a raw forwarded header inside Django.
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = USE_X_FORWARDED_PORT = False
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]  # Supervisor's local HTTP probe.
# The boundary rejects public HTTP before redirects. Apply short HSTS only to
# the active hostname; never preload or claim control of its subdomains.
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = "strict-origin"
X_FRAME_OPTIONS = "DENY"
APPEND_SLASH = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 16384
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10
DATA_UPLOAD_MAX_NUMBER_FILES = 0
PUBLIC_EVM_RPC_URL = ""
from urllib.parse import urlsplit
_internal_api = urlsplit(SPRING_BOOT_API_BASE_URL)
if (_internal_api.scheme not in ("http", "https") or _internal_api.hostname not in ("127.0.0.1", "localhost")
        or _internal_api.username or _internal_api.password or _internal_api.path not in ("", "/")
        or _internal_api.query or _internal_api.fragment):
    raise ValueError("The receiver's document API must be a local loopback origin.")
MIDDLEWARE = [
    "dashboard.receiver_surface.ReceiverBoundaryMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
# Django's default request/CSRF/error logging includes bearer paths. Never write
# request URLs, exception values, headers or traces from this public profile.
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"discard": {"class": "logging.NullHandler"}},
           "loggers": {name: {"handlers": ["discard"], "propagate": False}
                       for name in ("django", "waitress")}}
