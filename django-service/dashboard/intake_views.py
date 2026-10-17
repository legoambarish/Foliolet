"""Private, authenticated/CSRF-protected intake proxy; absent from receiver URLconf."""
import json
import hashlib
import re
from functools import wraps
from urllib.parse import urlsplit
from django.conf import settings
from django.http import JsonResponse
from django.core import signing
from django.views.decorators.http import require_GET, require_POST
from . import wallet_api as api
from . import tracked_files
from . import managed_intake


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
    folder = request.POST.get('folder', '')
    if not folder or request.POST.get('consent') != 'yes':
        raise ValueError()
    managed = getattr(settings, 'MANAGED_INTAKE', False)
    if managed and folder != settings.INTAKE_FOLDER:
        return JsonResponse({'error': 'Use the dedicated folder mounted into this container.'}, status=400)
    origin = urlsplit(settings.SPRING_BOOT_API_BASE_URL)
    if (origin.scheme != 'http' or origin.hostname not in ('127.0.0.1', 'localhost', '::1') or not origin.port
            or origin.username or origin.password or origin.path not in ('', '/') or origin.query or origin.fragment):
        raise ValueError()
    config = api.call('POST', '/api/wallet/intake/sessions', request.session['sb_auth'], payload={'folder': folder})
    host = '[::1]' if origin.hostname == '::1' else '127.0.0.1'
    config['apiUrl'] = f'http://{host}:{origin.port}'
    if managed:
        managed_intake.save(config, request.session['sb_auth'][0],
            settings.BASE_DIR.parent / '.local-data/managed-intake', settings.INTAKE_FOLDER)
        return JsonResponse({'managed': True, 'sessionId': config['sessionId']})
    response = JsonResponse(config)
    response['Content-Disposition'] = 'attachment; filename="foliolet-intake.json"'
    return response


@require_GET
@private
def sessions(request):
    return JsonResponse({'sessions': api.call('GET', '/api/wallet/intake/sessions', request.session['sb_auth'])})


def current_session(request):
    sessions = api.call('GET', '/api/wallet/intake/sessions', request.session['sb_auth'])
    return next((session for session in sessions if session.get('active')), None)


@require_GET
@private
def files(request):
    session = current_session(request)
    if not session:
        return JsonResponse({'sessionId': None, 'files': []})
    try:
        rows = tracked_files.inventory(session, request.session['sb_auth'][0])
    except (OSError, ValueError):
        return JsonResponse({'error': 'The paired folder is unavailable. Check it and retry.', 'files': []}, status=409)
    return JsonResponse({'sessionId': session['id'], 'folder': session['folder'], 'connected': session.get('connected', False), 'files': rows})


@require_POST
@private
def import_file(request):
    if int(request.META.get('CONTENT_LENGTH') or 0) > 8192:
        raise ValueError()
    session = current_session(request)
    if not session:
        return JsonResponse({'error': 'Enable a watcher pairing before importing from its folder.'}, status=409)
    try:
        relative, filename, content = tracked_files.read_selection(request.POST.get('selection', ''), session, request.session['sb_auth'][0])
    except (OSError, ValueError, signing.BadSignature):
        return JsonResponse({'error': 'The file or watcher pairing changed. Wait for the list to update, then select the file again.'}, status=409)
    result = api.call('POST', f"/api/wallet/intake/sessions/{session['id']}/import", request.session['sb_auth'],
        data={'relativePath': relative, 'folderHash': hashlib.sha256(session['folder'].encode()).hexdigest()},
        files={'file': (filename, content, 'application/octet-stream')})
    credential = result.get('id', '')
    if not re.fullmatch(r'0x[0-9a-f]{64}', credential):
        raise api.WalletAPIError('The document service returned an invalid document reference.')
    return JsonResponse({'id': credential, 'url': f'/wallet/{credential}/'})


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
