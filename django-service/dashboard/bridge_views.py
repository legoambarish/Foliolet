"""Role UI and bounded API proxy. Trust roots never come from a bundle."""
import json
import os
import re
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .decorators import spring_login_required
from . import wallet_api as api

def health(request):
    return JsonResponse({'status': 'UP'})

def pins():
    try:
        return json.loads(Path(os.environ.get('BRIDGE_PINS_FILE', settings.BASE_DIR.parent / '.bridge-data/config/bridge-pins.json')).read_text())
    except (OSError, ValueError):
        return {}

@spring_login_required
def home(request):
    return render(request, 'bridge/home.html', {'username': request.session.get('sb_username'), 'role': request.session.get('sb_role'), 'pins': pins(), 'product_label': 'Foliolet', 'publicBaseUrl': os.environ.get('PUBLIC_BASE_URL', '') if os.environ.get('PUBLIC_EXPOSURE_OPT_IN') == 'true' else ''})

@spring_login_required
def proxy(request, operation):
    allowed_get = {'state', 'assistant/documents', 'assistant/history'}
    allowed_post = {'holder-key', 'issue', 'governance', 'requests', 'draft', 'grants', 'decisions', 'plans', 'assistant/search', 'assistant/chat', 'imports/start', 'imports/xml', 'demo/rogue-scenario'}
    valid = operation in (allowed_get if request.method == 'GET' else allowed_post) or (request.method == 'GET' and re.fullmatch(r'(plans|imports)/[a-zA-Z0-9_:.-]{1,90}', operation)) or (request.method == 'POST' and re.fullmatch(r'(credentials|grants|plans|imports|assistant/history)/[a-zA-Z0-9_:.-]{1,90}/(revoke|retry|approve|cancel|execute|delete|consent|fetch|confirm)', operation))
    if request.method not in ('GET', 'POST') or not valid:
        return JsonResponse({'message': 'Unsupported operation'}, status=404)
    if len(request.body) > 262144:
        return JsonResponse({'message': 'Request too large'}, status=413)
    try:
        payload = json.loads(request.body) if request.body else None
        result = api.call(request.method, '/api/bridge/' + operation, request.session.get('sb_auth'), payload=payload)
        return JsonResponse(result, safe=isinstance(result, dict))
    except (ValueError, api.WalletAPIError) as exc:
        return JsonResponse({'message': str(exc)}, status=getattr(exc, 'status', 400))

@require_POST
@spring_login_required
def upload(request):
    file = request.FILES.get('file')
    if not file or file.size > 20 * 1024 * 1024:
        return JsonResponse({'message': 'Choose a source file smaller than 20 MiB'}, status=400)
    try:
        result = api.call('POST', '/api/wallet/documents', request.session.get('sb_auth'), data={'displayName': file.name, 'category': 'Education'}, files={'file': (file.name, file, file.content_type)})
        return JsonResponse(result)
    except api.WalletAPIError as exc:
        return JsonResponse({'message': str(exc)}, status=exc.status)

def share(request, token):
    return render(request, 'bridge/share.html', {'token': token, 'pins': pins(), 'product_label': 'Foliolet'})

@require_POST
def release(request, token):
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', token):
        return JsonResponse({'message': 'Invalid share'}, status=400)
    try:
        return JsonResponse(api.call('POST', f'/api/public/bridge/shares/{token}/open'))
    except api.WalletAPIError as exc:
        return JsonResponse({'message': str(exc)}, status=exc.status)

def share_status(request, token):
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', token):
        return JsonResponse({'message': 'Invalid share'}, status=400)
    try:
        return JsonResponse(api.call('GET', f'/api/public/bridge/shares/{token}/status'))
    except api.WalletAPIError as exc:
        return JsonResponse({'message': str(exc)}, status=exc.status)

def public_verifier(request):
    return render(request, 'bridge/public_verifier.html')

def discovery(request):
    return render(request, 'bridge/discovery.html')

def import_callback(request):
    # Callback is a signal only. Authenticated owner polls the provider status on the private desk.
    return render(request, 'bridge/import_callback.html')

@require_POST
@spring_login_required
def assistant_stream(request):
    import requests
    from django.http import StreamingHttpResponse
    if len(request.body) > 16384:
        return JsonResponse({'message': 'Question too large'}, status=413)
    try:
        payload = json.loads(request.body)
        upstream = requests.post(settings.SPRING_BOOT_API_BASE_URL + '/api/bridge/assistant/stream', auth=tuple(request.session['sb_auth']), json=payload, timeout=(5, 90), stream=True)
        if not upstream.ok:
            upstream.close()
            return JsonResponse({'message': 'Assistant unavailable'}, status=503)
    except (ValueError, requests.RequestException):
        return JsonResponse({'message': 'Assistant unavailable'}, status=503)
    def chunks():
        try:
            yield from upstream.iter_content(chunk_size=256)
        finally:
            upstream.close()
    response = StreamingHttpResponse(chunks(), content_type='text/event-stream')
    response['X-Accel-Buffering'] = 'no'
    return response
