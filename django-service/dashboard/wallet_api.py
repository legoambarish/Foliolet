"""Bounded private Spring bridge: local origin, no ambient proxies or redirects."""
import json
from urllib.parse import urlsplit
import requests
from django.conf import settings


class WalletAPIError(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def _origin():
    raw = settings.SPRING_BOOT_API_BASE_URL
    try:
        if not isinstance(raw, str) or any(ord(c) < 32 or ord(c) == 127 for c in raw):
            raise ValueError('Invalid origin')
        value = urlsplit(raw)
        if (value.scheme != 'http' or value.hostname not in ('localhost', '127.0.0.1', '::1')
                or value.username is not None or value.password is not None
                or value.path not in ('', '/') or value.query or value.fragment):
            raise ValueError('Invalid origin')
        port = value.port or 8080
        host = '[::1]' if value.hostname == '::1' else '127.0.0.1'
        return f'http://{host}:{port}'
    except (TypeError, ValueError) as exc:
        raise WalletAPIError('The private document service must use a valid local HTTP origin.') from exc


def call(method, path, auth=None, *, data=None, files=None, payload=None, binary=False):
    base = _origin()
    if (not isinstance(path, str) or not path.startswith('/api/')
            or any(ord(c) < 32 or ord(c) == 127 for c in path)
            or '#' in path or '\\' in path
            or method not in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD')):
        raise WalletAPIError('This private document operation is unavailable.', 404)
    if auth is not None and (not isinstance(auth, (tuple, list)) or len(auth) != 2
                            or not all(isinstance(v, str) and v for v in auth)):
        raise WalletAPIError('Sign in to use the private document service.', 401)
    limit = (21 if binary else 8) * 1024 * 1024
    try:
        with requests.Session() as client:
            client.trust_env = False
            with client.request(method, base + path, auth=tuple(auth) if auth else None,
                                data=data, files=files, json=payload, timeout=(5, 65),
                                allow_redirects=False, stream=True) as response:
                if 300 <= response.status_code < 400:
                    raise WalletAPIError('The local document service redirected the request. The redirect was refused.')
                body = bytearray()
                for chunk in response.iter_content(65536):
                    if len(body) + len(chunk) > limit:
                        raise WalletAPIError('The document service response exceeds the private viewer limit.')
                    body.extend(chunk)
                if not 200 <= response.status_code < 300:
                    message = 'The request could not be completed.'
                    try:
                        error = json.loads(body)
                        if isinstance(error, dict) and isinstance(error.get('message'), str):
                            message = error['message'][:500]
                    except (ValueError, UnicodeError):
                        pass  # Never reflect arbitrary HTML, proxy diagnostics or private error bodies.
                    if response.status_code == 401:
                        message = 'Your credentials were not accepted. Please sign in again.'
                    raise WalletAPIError(message, response.status_code)
                if binary:
                    return bytes(body), response.headers.get('Content-Disposition', 'attachment')
                try:
                    return json.loads(body)
                except (ValueError, UnicodeError):
                    return body.decode('utf-8', errors='replace')
    except requests.RequestException as exc:
        raise WalletAPIError('The document service is unavailable. No verification was completed.') from exc
