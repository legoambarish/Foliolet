"""Transient loopback receiver with actual middleware/API and Edge desktop/mobile.

HTTPS fixture requests are routed to the local Waitress origin, as a tunnel would
do, without opening a public tunnel. No fake verification or API responses.
"""
import json
import os
from pathlib import Path
import sys
import threading

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.local-data/p0/status-live'
os.environ.update(DJANGO_SETTINGS_MODULE='hermes.receiver_settings',SPRING_BOOT_API_BASE_URL=os.environ.get('INTAKE_TEST_API','http://127.0.0.1:8089'),
    FOLIOLET_PUBLIC_BASE_URL='https://p0-fixture.trycloudflare.com',FOLIOLET_RECEIVER_INSTANCE='p0-fixture')
sys.path.insert(0,str(ROOT/'django-service'))
from django.core.wsgi import get_wsgi_application
from waitress import create_server
from playwright.sync_api import sync_playwright

server=create_server(get_wsgi_application(),host='127.0.0.1',port=0,threads=4,
    trusted_proxy='127.0.0.1',trusted_proxy_headers={'x-forwarded-proto'},clear_untrusted_proxy_headers=True)
thread=threading.Thread(target=server.run,daemon=True);thread.start()
origin='https://p0-fixture.trycloudflare.com';local='http://127.0.0.1:'+str(server.effective_port)
fixture=json.loads((OUT/'checkpoint.json').read_text());checks=[]
def check(ok,name):
    assert ok,name
    checks.append(name);print('PASS',name,flush=True)
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        for profile in ('private','receiver'):
            context=browser.new_context(viewport={'width':1365,'height':1000})
            errors=[];context.on('weberror',lambda error:errors.append(str(error.error)))
            if profile=='receiver':
                def route_request(route):
                    request=route.request
                    if not request.url.startswith(origin+'/'):route.abort();return
                    response=route.fetch(url=local+request.url[len(origin):],headers={**request.headers,'host':'p0-fixture.trycloudflare.com','x-forwarded-proto':'https'})
                    route.fulfill(response=response)
                context.route('**/*',route_request)
                base=origin
            else:base=os.environ.get('INTAKE_TEST_UI','http://localhost:8018')
            page=context.new_page();page.goto(base+'/verify/'+fixture['token']+'/')
            page.get_by_role('button',name='Open disclosed facts',exact=True).click()
            page.get_by_text('Holder edited this suggestion',exact=True).wait_for()
            check(page.locator('[data-check="qr"].pass').count()==1 and page.locator('[data-check="branding"].pass').count()==1,profile+' positive detection stamps render green')
            check(page.get_by_text('Issuer not verified',exact=True).count()>0,profile+' issuer stays unverified')
            for width in (1365,390):
                page.set_viewport_size({'width':width,'height':900})
                check(page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),profile+' no overflow at '+str(width)+'px')
                page.screenshot(path=str(OUT/(profile+'-'+str(width)+'.png')),full_page=True)
            check(not errors,profile+' no browser errors')
            if profile=='receiver':
                response=page.goto(origin+'/wallet/')
                check(response.status==404,'public browser cannot reach holder wallet')
            context.close()
        browser.close()
finally:
    server.close()
(OUT/'browser-results.json').write_text(json.dumps({'checks':checks,'publicTransport':'actual loopback Waitress + locally routed HTTPS fixture; no public tunnel'},indent=2))
