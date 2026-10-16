"""Private, authenticated/CSRF-protected intake proxy; absent from receiver URLconf."""
import json
from functools import wraps
from urllib.parse import urlsplit
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from . import wallet_api as api


def private(view):
    @wraps(view)
    def guard(request, *args, **kwargs):
        if getattr(settings, 'RECEIVER_ONLY', False) or request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1'):
            return JsonResponse({'error': 'Private local application only.'}, status=404)
        if not request.session.get('sb_auth'):
            return JsonResponse({'error': 'Sign in to your wallet.'}, status=401)
        try:
            response = view(request, *args, **kwargs)
        except api.WalletAPIError as exc:
            response = JsonResponse({'error': str(exc)}, status=exc.status if 400 <= exc.status < 600 else 502)
        except (ValueError, TypeError, KeyError):
            response = JsonResponse({'error': 'Check the folder or document and retry.'}, status=400)
        response['Cache-Control'] = 'no-store, private'
        return response
    return guard


@require_POST
@private
def pair(request):
    if int(request.META.get('CONTENT_LENGTH') or 0) > 4096:
        raise ValueError()
    managed = getattr(settings, 'FOLIOLET_MANAGED_WATCHER', False)
    folder = settings.FOLIOLET_CONTAINER_INTAKE_FOLDER if managed else request.POST.get('folder', '')
    if not folder or request.POST.get('consent') != 'yes':
        raise ValueError()
    origin = urlsplit(settings.SPRING_BOOT_API_BASE_URL)
    if (origin.scheme != 'http' or origin.hostname not in ('127.0.0.1', 'localhost', '::1') or not origin.port
            or origin.username or origin.password or origin.path not in ('', '/') or origin.query or origin.fragment):
        raise ValueError()
    config = api.call('POST', '/api/wallet/intake/sessions', request.session['sb_auth'], payload={'folder': folder})
    host = '[::1]' if origin.hostname == '::1' else '127.0.0.1'
    config['apiUrl'] = f'http://{host}:{origin.port}'
    if managed:
        from .managed_watcher import enqueue
        try:
            enqueue(config)
        except (OSError, ValueError):
            # Do not leave an armed capability behind when local delivery fails.
            api.call('POST', f"/api/wallet/intake/sessions/{config['sessionId']}/stop", request.session['sb_auth'])
            return JsonResponse({'error': 'The local companion is unavailable. Retry or use manual upload.'}, status=503)
        return JsonResponse({'managed': True, 'sessionId': config['sessionId']})
    response = JsonResponse(config)
    response['Content-Disposition'] = 'attachment; filename="foliolet-intake.json"'
    return response


@require_GET
@private
def sessions(request):
    rows = api.call('GET', '/api/wallet/intake/sessions', request.session['sb_auth'])
    if getattr(settings, 'FOLIOLET_MANAGED_WATCHER', False):
        for row in rows:
            if row.get('folder') == settings.FOLIOLET_CONTAINER_INTAKE_FOLDER:
                row['folder'] = settings.FOLIOLET_HOST_INTAKE_FOLDER
    return JsonResponse({'sessions': rows})


@require_POST
@private
def stop(request, session_id):
    return JsonResponse(api.call('POST', f'/api/wallet/intake/sessions/{session_id}/stop', request.session['sb_auth']))


@require_GET
@private
def analysis(request, credential_id):
    return JsonResponse(api.call('GET', f'/api/wallet/intake/documents/{credential_id}', request.session['sb_auth']))


@require_POST
@private
def retry(request, credential_id):
    return JsonResponse(api.call('POST', f'/api/wallet/intake/documents/{credential_id}/retry', request.session['sb_auth']))
