"""Authenticated private Ask Foli surface. Never imported by receiver_urls."""
import json
import re
from functools import wraps
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods
from . import foli_api


def private(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if getattr(settings, 'RECEIVER_ONLY', False) or request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1'):
            return JsonResponse({'code': 'PRIVATE_ONLY', 'message': 'Foli is available in the private local application.'}, status=404)
        if not request.session.get('sb_auth'):
            if request.path == '/ask-foli/':
                return redirect('dashboard:login')
            return JsonResponse({'code': 'SIGNED_OUT', 'message': 'Sign in to use Foli.'}, status=401)
        try:
            return view(request, *args, **kwargs)
        except foli_api.FoliAPIError as exc:
            return JsonResponse({'code': exc.code, 'message': exc.message}, status=exc.status)
        except (ValueError, TypeError, UnicodeDecodeError):
            return JsonResponse({'code': 'INVALID_REQUEST', 'message': 'Check the question and selected source, then retry.'}, status=400)
    return guarded


@require_GET
@ensure_csrf_cookie
@private
def home(request):
    return render(request, 'wallet/foli.html', {'product_label': settings.PRODUCT_LABEL,
                  'current_username': request.session.get('sb_username')})


def proxy(request, path, **kwargs):
    body, status = foli_api.call(request.method, path, request.session['sb_auth'], **kwargs)
    if kwargs.get('image'):
        return HttpResponse(body, content_type='image/png', status=status)
    return JsonResponse(body, safe=isinstance(body, dict), status=status)


@require_GET
@private
def documents(request):
    return proxy(request, 'documents')


@require_GET
@private
def health(request):
    return proxy(request, 'health')


@require_http_methods(['POST'])
@private
def jobs(request):
    if request.content_type != 'application/json':
        return JsonResponse({'code': 'JSON_REQUIRED', 'message': 'Send a JSON question.'}, status=415)
    if int(request.META.get('CONTENT_LENGTH') or 0) > 32768:
        return JsonResponse({'code': 'REQUEST_LIMIT', 'message': 'The question is too large.'}, status=413)
    raw = request.body
    if len(raw) > 32768:
        return JsonResponse({'code': 'REQUEST_LIMIT', 'message': 'The question is too large.'}, status=413)
    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) - {'documentId', 'question', 'mode', 'history', 'sourceHash', 'cloudConsent'}:
        raise ValueError()
    if 'cloudConsent' in payload and not isinstance(payload['cloudConsent'], bool):
        raise ValueError()
    return proxy(request, 'jobs', payload=payload)


@require_http_methods(['GET', 'DELETE'])
@private
def job(request, job_id):
    return proxy(request, 'jobs/' + str(job_id))


@require_http_methods(['DELETE'])
@private
def memory(request):
    return proxy(request, 'memory')


@require_GET
@private
def source(request, image=False):
    if set(request.GET) != {'documentId', 'hash', 'page'} or any(len(request.GET.getlist(k)) != 1 for k in request.GET):
        raise ValueError()
    doc = request.GET['documentId']
    if not re.fullmatch(r'(?:wallet:0x[0-9a-f]{64}|legacy:[1-9][0-9]{0,18})', doc):
        raise ValueError()
    if not re.fullmatch(r'[0-9a-f]{64}', request.GET['hash']) or not 1 <= int(request.GET['page']) <= 5000:
        raise ValueError()
    return proxy(request, 'page' if image else 'source', params=request.GET.dict(), image=image)
