"""Narrow private proxy: session credentials, numeric loopback, no fallbacks."""
import json
import re
from urllib.parse import urlsplit
import requests
from django.conf import settings


class FoliAPIError(Exception):
    def __init__(self, code, message, status=503):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def origin():
    value = urlsplit(settings.SPRING_BOOT_API_BASE_URL)
    if (value.scheme != 'http' or value.hostname not in ('localhost', '127.0.0.1', '::1')
            or value.username or value.password or value.path not in ('', '/') or value.query or value.fragment):
        raise FoliAPIError('LOCAL_CONFIG', 'Foli requires a local document service.')
    host = '[::1]' if value.hostname == '::1' else '127.0.0.1'
    return f'http://{host}:{value.port or 8080}'


def call(method, path, auth, *, payload=None, params=None, image=False):
    allowed = (method == 'GET' and path in ('documents', 'health', 'source', 'page')
               or method == 'POST' and path == 'jobs'
               or method == 'DELETE' and path == 'memory'
               or method in ('GET', 'DELETE') and re.fullmatch(r'jobs/[0-9a-f-]{36}', path))
    if not allowed:
        raise FoliAPIError('INVALID_ROUTE', 'This Foli operation is unavailable.', 404)
    if not isinstance(auth, (list, tuple)) or len(auth) != 2 or not all(isinstance(v, str) and v for v in auth):
        raise FoliAPIError('SIGNED_OUT', 'Sign in to use Foli.', 401)
    try:
        with requests.Session() as client:
            client.trust_env = False
            with client.request(method, origin() + '/api/foli/' + path, auth=tuple(auth), json=payload,
                                params=params, headers={'X-Foli-Client': 'private'}, timeout=(3, 25),
                                allow_redirects=False, stream=True) as response:
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > 8 * 1024 * 1024:
                        raise FoliAPIError('RESPONSE_LIMIT', 'This result exceeds the private viewer limit. Try a narrower question.')
                if not 200 <= response.status_code < 300:
                    if response.status_code == 401:
                        raise FoliAPIError('SIGNED_OUT', 'Your session is no longer authorized. Sign in again.', 401)
                    if 300 <= response.status_code < 400:
                        raise FoliAPIError('LOCAL_CONFIG', 'The local service redirected the request. Foli refused the redirect.')
                    try:
                        error = json.loads(body)
                        code = str(error.get('code', 'UNAVAILABLE'))[:80]
                        message = str(error.get('message', 'The private reading request could not be completed.'))[:500]
                    except (ValueError, AttributeError):
                        code, message = 'UNAVAILABLE', 'The private reading request could not be completed.'
                    raise FoliAPIError(code, message, response.status_code)
                if image:
                    if response.headers.get('Content-Type', '').split(';')[0] != 'image/png' or not body.startswith(b'\x89PNG\r\n\x1a\n'):
                        raise FoliAPIError('INVALID_PREVIEW', 'The local service did not return a page image.')
                    return bytes(body), response.status_code
                try:
                    return json.loads(body), response.status_code
                except ValueError as exc:
                    raise FoliAPIError('INVALID_RESPONSE', 'The local service returned an unreadable response.') from exc
    except requests.RequestException as exc:
        raise FoliAPIError('SERVICE_OFFLINE', 'The local document service is unavailable. Start Spring and retry.') from exc
