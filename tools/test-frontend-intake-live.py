"""Actual branch runtime: fresh fictional account, upload, OCR, reread and confirmation.

Requires isolated loopback Spring/Django services and benchmark fictional fixtures.
Never starts a tunnel, reads another account, or contacts an external AI provider.
"""
import json
import os
from pathlib import Path
import secrets
import time
import requests
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/refresh-live-ui'
OUT.mkdir(parents=True, exist_ok=True)
UI = os.environ.get('INTAKE_TEST_UI', 'http://127.0.0.1:8038')
API = os.environ.get('INTAKE_TEST_API', 'http://127.0.0.1:8068')
assert UI.startswith('http://127.0.0.1:') and API.startswith('http://127.0.0.1:')
http = requests.Session()
http.trust_env = False
auth = ('refresh-' + secrets.token_hex(5), secrets.token_urlsafe(24))
r = http.post(API + '/api/auth/register', json={'username': auth[0], 'password': auth[1], 'role': 'HOLDER'}, timeout=15)
r.raise_for_status()
checks = []


def passed(name):
    checks.append(name)
    print(time.strftime('%H:%M:%S'), 'PASS', name, flush=True)


def status(credential):
    response = http.get(API + '/api/wallet/intake/documents/' + credential, auth=auth, timeout=15)
    response.raise_for_status()
    return response.json()


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width': 1365, 'height': 1000}, reduced_motion='reduce')
    page = context.new_page()
    errors, external = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def restrict(route):
        if route.request.url.startswith((UI+'/', API+'/', 'data:', 'blob:')):
            route.continue_()
        else:
            external.append(route.request.url.split('?')[0])
            route.abort()

    context.route('**/*', restrict)
    page.goto(UI + '/login/')
    page.locator('#username').fill(auth[0])
    page.locator('#password').fill(auth[1])
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url(UI + '/')
    for kind in ('native', 'scan'):
        page.goto(UI + '/wallet/enroll/')
        page.locator('#file').set_input_files(str(ROOT / f'.local-data/refresh-benchmark/broad-fields-{kind}.pdf'))
        page.locator('#name').fill('Fictional broad-field ' + kind)
        page.get_by_role('button', name='Upload and review facts', exact=True).click()
        page.wait_for_url('**/wallet/0x*/')
        credential = page.url.rstrip('/').split('/')[-1]
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            current = status(credential)
            if current['state'] not in ('QUEUED', 'RUNNING'):
                break
            print(time.strftime('%H:%M:%S'), kind, current['stage'], flush=True)
            page.wait_for_timeout(2500)
        else:
            raise AssertionError('Live reading timed out')
        fields = current['report']['currentFields']
        assert len(fields) == 12, (kind, len(fields), current['report']['diagnostics'])
        assert next(f['value'] for f in fields if f['label'] == 'Customer Number') == '0000719'
        assert current['issuer'] == 'NOT_VERIFIED'
        if kind == 'native':
            expect(page.locator('[name=claim_value]')).to_have_count(12, timeout=30000)
            assert all(f['support']['quality'] == 'SUPPORTED' for f in fields)
            source = page.locator('.scan-note a').first.get_attribute('href')
            response = context.request.get(UI + source)
            assert response.status == 200 and 'image/png' in response.headers['content-type']
            passed('Real native PDF yields 12 exact fields, literal leading-zero IDs, and source-page preview')
            old_attempt = current['attempts']
            page.locator('#retry-intake').click()
            expect(page.locator('#retry-intake')).to_be_enabled(timeout=30000)
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                current = status(credential)
                if current['attempts'] > old_attempt and current['state'] not in ('QUEUED','RUNNING'):
                    break
                page.wait_for_timeout(1500)
            assert current['fields'] == fields, 'The original baseline changed'
            passed('Real reread completes and preserves the original server baseline')
        else:
            expect(page.locator('.use-reviewed-fact')).to_have_count(12, timeout=30000)
            assert page.locator('[name=claim_value]').first.input_value() == ''
            page.locator('.use-reviewed-fact').first.click()
            assert page.locator('[name=claim_value]').first.input_value()
            page.locator('[name=claim_value]').first.fill('Holder checked and edited')
            passed('Real scanned PDF surfaces 12 review fields and requires explicit acceptance')
        for width, theme in ((1365, 'light'), (390, 'dark')):
            page.set_viewport_size({'width': width, 'height': 900})
            page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(OUT / f'{kind}-{width}-{theme}.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        page.locator('[name=confirm]').check()
        page.get_by_role('button', name='Confirm facts', exact=True).click()
        page.wait_for_load_state('networkidle')
        result = status(credential)
        expected = 'SUGGESTIONS_UNMODIFIED' if kind == 'native' else 'SUGGESTIONS_MODIFIED'
        assert result['lineage'] == expected, result['lineage']
        assert result['issuer'] == 'NOT_VERIFIED'
        passed(f'{kind}: confirmation correctly records {expected}; issuer authority remains unverified')
    assert not errors, errors
    assert not external, external
    passed('Real branch UI has no JavaScript errors or external document requests; desktop/mobile checked')
    browser.close()
(OUT / 'results.json').write_text(json.dumps({'passed': len(checks), 'checks': checks, 'runtime': 'isolated real branch services'}, indent=2))
