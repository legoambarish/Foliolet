"""HTTP boundary for the receiver, not a second disclosure authorization engine."""
import hashlib
import ipaddress
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from . import wallet_views

ASSETS = {
    "wallet/theme.js": "text/javascript",
    "wallet/wallet.js": "text/javascript",
    "wallet/verify.js": "text/javascript",
    "wallet/wallet.css": "text/css",
    "wallet/fonts/public-sans-var.woff2": "font/woff2",
    "wallet/fonts/source-serif-4-var.woff2": "font/woff2",
    "wallet/fonts/plex-mono-400.woff2": "font/woff2",
    "wallet/fonts/plex-mono-500.woff2": "font/woff2",
}


def protected(response):
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "strict-origin"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Frame-Options"] = "DENY"
    response["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
        "frame-ancestors 'none'; form-action 'self'; base-uri 'none'; object-src 'none'"
    )
    return response


class ReceiverBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.lock = threading.Lock()
        self.buckets = {}
        self.salt = secrets.token_bytes(32)

    def __call__(self, request):
        # Host is checked exactly; the rotating suffix allowance exists only in
        # the receiver profile and never permits another trycloudflare tenant.
        origin = settings.PUBLIC_RECEIVER_ORIGIN
        expected = urlsplit(origin).netloc if origin else ""
        host = request.META.get("HTTP_HOST", "")
        local_health = (request.path == "/healthz/" and host.split(":")[0] == "127.0.0.1"
                        and request.META.get("REMOTE_ADDR") == "127.0.0.1")
        if not local_health and (not expected or host != expected):
            return protected(HttpResponse("Invalid receiver host.", status=400))
        if not local_health and not request.is_secure():
            return protected(HttpResponse("HTTPS is required.", status=403))
        if request.method not in ("GET", "HEAD", "POST"):
            return protected(HttpResponse(status=405))
        try:
            size = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            return protected(HttpResponse(status=400))
        if size < 0 or size > 16384:
            return protected(HttpResponse("Request too large.", status=413))
        if not local_health and not request.path.startswith("/static/"):
            # Cloudflare supplies CF-Connecting-IP; do not trust user-supplied
            # X-Forwarded-For. Keep only salted, ephemeral bucket identifiers.
            try:
                ip = str(ipaddress.ip_address(request.META.get("HTTP_CF_CONNECTING_IP", "")))
            except ValueError:
                ip = request.META.get("REMOTE_ADDR", "unknown")
            key = hashlib.sha256(self.salt + ip.encode()).digest()
            if not self._admit(key, request.method == "POST"):
                response = HttpResponse("Too many requests. Try again shortly.", status=429)
                response["Retry-After"] = "60"
                return protected(response)
        return protected(self.get_response(request))

    def _admit(self, key, post):
        window = int(time.monotonic() // 60)
        with self.lock:
            self.buckets = {k: v for k, v in self.buckets.items() if v[0] == window}
            if len(self.buckets) >= 4096 and (key, post) not in self.buckets:
                return False
            for bucket, limit in (((key, post), 12 if post else 90),
                                  ((b"global", post), 120 if post else 600)):
                count = self.buckets.get(bucket, (window, 0))[1]
                if count >= limit:
                    return False
            for bucket in ((key, post), (b"global", post)):
                self.buckets[bucket] = (window, self.buckets.get(bucket, (window, 0))[1] + 1)
            return True


@require_http_methods(["GET", "HEAD"])
def health(request):
    return JsonResponse({"service": "foliolet-receiver", "instance": settings.PUBLIC_RECEIVER_INSTANCE})


@require_http_methods(["GET", "HEAD"])
def static_asset(request, asset):
    if asset not in ASSETS:
        raise Http404
    source = Path(__file__).parent / "static" / asset
    return FileResponse(source.open("rb"), content_type=ASSETS[asset])


@require_http_methods(["GET", "HEAD"])
def proof_status(request, grant_id):
    if grant_id not in request.session.get("released_proofs", {}):
        raise Http404
    return wallet_views.proof_status(request, grant_id)


def csrf_failure(request, reason=""):
    return protected(HttpResponse("The form could not be accepted. Reload the receiver page and try again.", status=403))
