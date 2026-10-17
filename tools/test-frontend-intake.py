"""Real Edge against this branch's rendered templates/assets with controlled API replies.

Run frontend-preview/render.py .local-data/refresh-ui first. No real records or
services are contacted. Complements Java workflow and live PDF/OCR tests.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / '.local-data/refresh-ui'
OUT = ROOT / '.local-data/refresh-ui-results'
OUT.mkdir(parents=True, exist_ok=True)
ORIGIN = 'http://127.0.0.1:8919'
checks = []


def field(value='91', quality='SUPPORTED'):
    return dict(path='education.math', label='Mathematics marks', type='decimal', value=value, evidence='Mathematics ' + value,
                citation=dict(documentId='wallet:0x'+'a'*64, sourceHash='b'*64, page=1, provenance='Embedded text'),
                support=dict(quality=quality, reasons=['OCR_REQUIRES_VISUAL_REVIEW'] if quality == 'REVIEW_REQUIRED' else []))


state = dict(state='READY', attempts=1, stage='Current reading complete', fields=[field()], report={'currentFields': [field()]}, stamps=[])


def passed(name):
    checks.append(name)
    print('PASS', name, flush=True)


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width': 1365, 'height': 1000}, reduced_motion='reduce')
    page = context.new_page()
    errors, external = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def route(request):
        url = request.request.url
        if not url.startswith(ORIGIN + '/'):
            external.append(url)
            request.abort()
            return
        path = url[len(ORIGIN):].split('?')[0]
        if '/intake/' in path:
            request.fulfill(json=state)
            return
        if path.startswith('/static/'):
            asset = PREVIEW / path.lstrip('/')
            if asset.is_file():
                mime = 'application/javascript' if asset.suffix == '.js' else 'text/css' if asset.suffix == '.css' else 'image/svg+xml' if asset.suffix == '.svg' else 'application/octet-stream'
                request.fulfill(path=str(asset), content_type=mime)
            else:
                request.fulfill(status=404, body='')
            return
        request.fulfill(path=str(PREVIEW / 'wallet/doc-draft-7f2a/index.html'), content_type='text/html')

    context.route('**/*', route)
    page.goto(ORIGIN + '/wallet/doc-draft-7f2a/')
    values = page.locator('[name=claim_value]')
    page.wait_for_function("document.querySelector('[name=claim_value]').value === '91'")
    assert values.count() == 1
    passed('Current supported field populates the actual redesigned review template')

    def reread(fields):
        state['attempts'] += 1
        state['report']['currentFields'] = fields
        page.locator('#retry-intake').click()
        page.wait_for_function("!document.getElementById('retry-intake').disabled")

    reread([])
    assert values.count() == 1 and values.first.input_value() == ''
    assert page.locator('#intake-review').inner_text() == ''
    assert 'Mathematics 91' not in page.locator('#fact-rows').inner_text()
    passed('Empty reread clears obsolete rows and evidence without restoring the immutable baseline')
    reread([field('86', 'REVIEW_REQUIRED')])
    assert values.first.input_value() == ''
    assert page.locator('.use-reviewed-fact').count() == 1
    page.locator('.use-reviewed-fact').click()
    assert values.first.input_value() == '86'
    assert page.locator('.use-reviewed-fact').is_disabled()
    values.first.fill('88')
    reread([field('92')])
    assert values.first.input_value() == '88'
    assert '92' in page.locator('#intake-review').inner_text()
    assert '86' not in page.locator('#intake-review').inner_text()
    assert page.locator('.use-reviewed-fact').is_disabled()
    passed('OCR review requires acceptance; rereads preserve edits, refresh evidence, and prevent duplicate paths')

    for status in ('PASSED', 'NOT_DETECTED', 'INCONCLUSIVE', 'NOT_CHECKED', 'NOT_APPLICABLE', 'FAILED'):
        state['stamps'] = [dict(id='qr', tone='pass' if status == 'PASSED' else 'fail' if status == 'FAILED' else 'quiet',
                               state=status, label='DigiLocker-associated QR', display=status, detail='Provisional detection only')]
        reread([field()])
        tag = page.locator('#intake-labels [data-check=qr]')
        assert tag.count() == 1 and tag.get_attribute('data-state') == status
        assert ('✓' in tag.inner_text()) == (status == 'PASSED')
        assert ('pass' in tag.get_attribute('class').split()) == (status == 'PASSED')
    passed('Status labels replace previous results; pass icon and color turn off for non-passing states')
    for width, theme in ((1365, 'light'), (390, 'light'), (390, 'dark')):
        page.set_viewport_size({'width': width, 'height': 900})
        page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
        page.evaluate('window.scrollTo(0, 0)')
        page.screenshot(path=str(OUT / f'review-{width}-{theme}.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), page.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).map(e => ({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width})).slice(0,20)")
    passed('Desktop and phone layouts fit in light and dark modes')
    # Reload resets browser edits; source fragments remain text, never executable markup.
    malicious = field('<img src=x onerror=alert(1)>')
    state['report']['currentFields'] = [malicious]
    page.reload()
    page.wait_for_function("document.querySelector('[name=claim_value]').value.startsWith('<img')")
    assert page.locator('#fact-rows img').count() == 0
    passed('Document text is escaped and cannot execute as markup')
    assert not errors, errors
    assert not external, external
    passed('No JavaScript errors or external requests')
    browser.close()
(OUT / 'results.json').write_text(json.dumps({'checks': checks, 'passed': len(checks), 'api': 'controlled fixtures', 'browser': 'Edge'}, indent=2))
