"""Real Edge regression gate for page-lifetime chat history.

Renders this checkout's actual Django page and serves its actual assets. API
replies are controlled fixtures: no model, private records, or running services
are used. Run: .venv/Scripts/python.exe tools/test-foli-history.py
"""
import json
import mimetypes
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'django-service'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hermes.settings')
import django
django.setup()
from django.contrib.staticfiles import finders
from django.test import RequestFactory
from django.urls import resolve
from dashboard.foli_views import home
from playwright.sync_api import sync_playwright, expect

request = RequestFactory().get('/ask-foli/')
request.session = {'sb_auth': ['history-fixture', 'synthetic'], 'sb_username': 'history-fixture'}
request.resolver_match = resolve('/ask-foli/')
html = home(request).content.decode()
ORIGIN = 'http://127.0.0.1:8919'
OUT = ROOT / '.local-data/foli-history'
OUT.mkdir(parents=True, exist_ok=True)
docs = [dict(id='wallet:' + key, name=name, filename=name + '.txt', version=1,
             format='txt', status='DRAFT', supported=True)
        for key, name in [('a', 'Document A'), ('b', 'Document B')]]
source_text = 'A synthetic fee of 9300 is due.'
hostile = '<img src=x onerror=window.__foliXss=1>'
calls, checks, errors, external, held = [], [], [], [], {}
signed_out = False


def passed(name):
    checks.append(name)
    print('PASS', name, flush=True)


def manifest(document_id):
    return dict(documentId=document_id, sourceHash='b' * 64, format='txt', readablePages=1,
                totalPages=1, accountedPages=1, complete=True, warnings=[],
                pages=[dict(number=1, status='READABLE', warnings=[])])


def answer(payload):
    citation = dict(id='E1', documentId=payload.get('documentId'), sourceHash='b' * 64,
                    page=1, provenance='Embedded text', start=0, end=len(source_text), quote=source_text)
    result = dict(answer='Select a document from Your sources first.',
                  answerKind='DOCUMENT_REQUIRED', citations=[], warnings=[])
    if payload.get('documentId'):
        result.update(answer='Answer to ' + payload['question'] + ' ' + hostile,
                      answerKind='INTERPRETATION', citations=[citation], manifest=manifest(payload['documentId']))
    if payload['mode'] == 'review':
        result.update(answer='Review of synthetic source [E1]', answerKind='DOCUMENT_REVIEW',
                      reviewCoverage=dict(checklistPages=1, totalPages=1, semanticChunks=1, totalChunks=1, semanticComplete=True),
                      findings=[dict(title='Synthetic fee', categories=['fees'], citations=[citation],
                                     explanation=source_text, definitions=[], references=[], warnings=[])])
    return result


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel=os.environ.get('FOLI_BROWSER_CHANNEL', 'msedge'), headless=True)
    context = browser.new_context(viewport={'width': 1365, 'height': 1000}, reduced_motion='reduce')
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))

    def route(route):
        req = route.request
        if not req.url.startswith(ORIGIN + '/'):
            external.append(req.url)
            route.abort()
            return
        path = urlsplit(req.url).path
        if path.startswith('/static/'):
            asset = finders.find(path.removeprefix('/static/'))
            if asset:
                route.fulfill(path=asset, content_type=mimetypes.guess_type(asset)[0] or 'application/octet-stream')
            else:
                route.fulfill(status=404, body='')
        elif path == '/ask-foli/':
            route.fulfill(body=html, content_type='text/html')
        elif path.endswith('/documents/'):
            route.fulfill(json=docs)
        elif path.endswith('/health/'):
            route.fulfill(status=401 if signed_out else 200, json=(dict(code='SIGNED_OUT') if signed_out else
                          dict(ollama=dict(status='READY', model='fixture', cloudDisabled=True), ocr='local', geminiAvailable=True)))
        elif path.endswith('/source/'):
            route.fulfill(json=dict(document=dict(format='txt'), page=dict(number=1, text=source_text, status='READABLE', warnings=[])))
        elif path.endswith('/jobs/'):
            payload = req.post_data_json
            calls.append(payload)
            if payload['question'] in ('Delayed creation', 'Delayed completion'):
                if payload['question'] == 'Delayed creation':
                    held['create'] = route
                else:
                    route.fulfill(json=dict(id='slow', state='RUNNING', stage='Reading'))
            else:
                route.fulfill(json=dict(id='done', state='COMPLETE', result=(manifest(payload['documentId']) if payload['mode'] == 'index' else answer(payload))))
        elif path.endswith('/jobs/slow/'):
            held['delete' if req.method == 'DELETE' else 'poll'] = route
        elif path.endswith('/jobs/late/') and req.method == 'DELETE':
            held['late_cancelled'] = True
            route.fulfill(json=dict(state='CANCELLED'))
        else:
            raise AssertionError('Unexpected request: ' + req.method + ' ' + path)

    context.route('**/*', route)

    def idle():
        expect(page.locator('#foli-progress')).to_be_hidden()

    def select(name):
        target = page.locator('#foli-general') if name == 'general' else page.locator('#foli-documents button').filter(has_text=name)
        target.click()
        idle()

    def ask(text):
        page.locator('#foli-question').fill(text)
        page.locator('#foli-send').click()
        idle()

    def log():
        return page.locator('#foli-log').inner_text()

    def wait_held(key):
        for _ in range(100):
            if key in held:
                return held.pop(key)
            page.wait_for_timeout(30)
        raise AssertionError('Request not observed: ' + key)

    try:
        page.goto(ORIGIN + '/ask-foli/')
        expect(page.locator('#foli-documents button')).to_have_count(2)
        expect(page.locator('#foli-document-title')).to_have_text('Choose a document')
        ask('General first question')
        assert 'Select a document from Your sources first.' in log()
        assert page.locator('.foli-citation').count() == 0
        passed('No-document response invites source selection and has no citations')
        general = log()
        page.locator('#foli-question').fill('General draft')
        select('Document A')
        assert log() == ''
        for index in range(5):
            ask('A question ' + str(index))
        assert len(calls[-1]['history']) == 6
        assert all('A question' in item['text'] for item in calls[-1]['history'])
        page.locator('#foli-review').click()
        idle()
        a_log = log()
        assert 'A question 0' in a_log and 'Synthetic fee' in a_log
        page.locator('#foli-question').fill('A draft')
        page.locator('#foli-cloud-consent').check()
        select('Document B')
        assert log() == ''
        expect(page.locator('#foli-cloud-consent')).not_to_be_checked()
        ask('B question')
        assert calls[-1]['history'] == []
        b_log = log()
        select('general')
        assert log() == general
        expect(page.locator('#foli-question')).to_have_value('General draft')
        ask('General followup')
        assert calls[-1]['history'][0]['text'] == 'General first question'
        assert all('A question' not in item['text'] for item in calls[-1]['history'])
        general = log()
        for _ in range(3):
            select('Document A')
            assert log() == a_log
            expect(page.locator('#foli-question')).to_have_value('A draft')
            select('Document B')
            assert log() == b_log
        passed('General and two document chats restore full transcripts, reviews and drafts without duplication; model context stays isolated and bounded')

        select('Document A')
        page.get_by_label('Filter fine-print findings').select_option('fees')
        page.locator('.foli-citation').first.click()
        expect(page.locator('#foli-source-text mark')).to_have_text(source_text)
        page.locator('#foli-source-close').click()
        assert page.locator('#foli-log img, #foli-log script').count() == 0
        assert page.evaluate('window.__foliXss') is None
        passed('Restored citation controls and review filters work; model HTML remains inert text')

        page.locator('#foli-clear').click()
        assert log() == ''
        expect(page.locator('#foli-question')).to_have_value('')
        select('Document B')
        assert log() == b_log
        select('Document A')
        assert log() == ''
        ask('Fresh A question')
        assert calls[-1]['history'] == []
        select('general')
        assert log() == general
        page.locator('#foli-clear').click()
        select('Document B')
        assert log() == b_log
        select('general')
        assert 'General first question' not in log()
        ask('Fresh general question')
        assert calls[-1]['history'] == []
        passed('Clear affects only the open conversation and resets its model context across later switches')

        page.locator('#foli-question').fill('Delayed creation')
        page.locator('#foli-send').click()
        creation = wait_held('create')
        select('Document A')
        creation.fulfill(json=dict(id='late', state='COMPLETE', result=dict(answer='STALE CREATION', answerKind='GENERAL')))
        wait_held('late_cancelled')
        assert 'STALE CREATION' not in log()
        passed('A job created after switching is cancelled and cannot append to another conversation')

        page.locator('#foli-question').fill('Delayed completion')
        page.locator('#foli-send').click()
        poll = wait_held('poll')
        # The first cancellation is deliberately held while another chat is selected.
        page.locator('#foli-documents button').filter(has_text='Document B').click()
        cancellation = wait_held('delete')
        # History is already visible, even though new indexing waits for cancellation.
        assert log() == b_log
        call_count = len(calls)
        select('general')
        cancellation.fulfill(json=dict(state='CANCELLED'))
        poll.fulfill(json=dict(id='slow', state='COMPLETE', result=dict(answer='STALE COMPLETION', answerKind='GENERAL')))
        expect(page.locator('#foli-document-title')).to_have_text('Choose a document')
        assert len(calls) == call_count
        select('Document A')
        assert 'STALE COMPLETION' not in log()
        select('Document B')
        assert log() == b_log
        passed('Rapid switches finish on the latest chat even with slow cancellation and late results')

        page.locator('#foli-question').fill('Delayed completion')
        page.locator('#foli-send').click()
        poll = wait_held('poll')
        page.locator('#foli-clear').click()
        cancellation = wait_held('delete')
        cancellation.fulfill(json=dict(state='CANCELLED'))
        poll.fulfill(json=dict(id='slow', state='COMPLETE', result=dict(answer='CLEARED LATE REPLY', answerKind='GENERAL')))
        select('general')
        select('Document B')
        assert log() == ''
        passed('Clear during a pending response cannot resurrect the conversation')

        for width in (1365, 390):
            page.set_viewport_size({'width': width, 'height': 1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            expect(page.get_by_role('button', name='Clear conversation', exact=True)).to_be_visible()
        page.screenshot(path=str(OUT / 'mobile.png'), full_page=True)
        passed('Clear control is usable on desktop and 390px mobile without overflow')

        page.reload()
        expect(page.locator('#foli-documents button')).to_have_count(2)
        assert 'Fresh general question' not in log()
        select('Document A')
        assert log() == ''
        select('Document B')
        assert log() == ''
        passed('Reload discards every conversation')

        ask('Private B question')
        select('Document A')
        ask('Private A question')
        signed_out = True
        page.locator('#foli-health').click()
        expect(page.locator('#foli-document-title')).to_have_text('Signed out')
        assert log() == ''
        expect(page.locator('#foli-documents button')).to_have_count(0)
        page.locator('#foli-general').click()
        assert log() == ''
        expect(page.locator('#foli-clear')).to_be_disabled()
        expect(page.locator('#foli-send')).to_be_disabled()
        passed('Authorization loss wipes all cached chats and blocks stale conversation restoration')
        assert not errors, errors
        assert not external, external
        passed('No JavaScript exceptions, external calls, or unrelated API mutations')
    finally:
        (OUT / 'results.json').write_text(json.dumps(dict(checks=checks, errors=errors, external=external), indent=2))
        browser.close()
