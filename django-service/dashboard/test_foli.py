"""Private Foli integration, proxy confinement, CSRF and receiver regressions."""
import json
import logging
from unittest.mock import MagicMock, patch
from django.test import Client, SimpleTestCase, TestCase, override_settings
from . import foli_api
from .wallet_security import ReceiverRequestLogFilter
from .test_receiver import PROFILE, HOST

DOC='wallet:0x'+'a'*64
JOB='f155aa10-970b-4af8-8ea3-98dd8fdc3c72'
HASH='b'*64


class FoliPrivateTests(TestCase):
    def setUp(self):
        session=self.client.session
        session['sb_auth']=['synthetic-holder','test-only-secret']
        session['sb_username']='synthetic-holder'
        session.save()

    def test_page_has_native_navigation_no_credentials_and_strict_csp(self):
        response=self.client.get('/ask-foli/')
        self.assertContains(response,'Ask Foli')
        self.assertContains(response,'href="/ask-foli/" data-tip="Ask Foli" aria-current="page"')
        self.assertContains(response,'wallet/foli.js')
        self.assertContains(response,'wallet/foli.css')
        self.assertNotContains(response,'test-only-secret')
        self.assertNotContains(response,'11434')
        self.assertIn("connect-src 'self';",response['Content-Security-Policy'])
        self.assertNotIn('https:',response['Content-Security-Policy'])
        self.assertEqual(response['Cache-Control'],'no-store, private')

    def test_anonymous_page_redirect_and_json_routes_denied(self):
        client=Client()
        self.assertEqual(client.get('/ask-foli/').status_code,302)
        for path in ('documents/','health/','source/','page/','jobs/'+JOB+'/'):
            self.assertEqual(client.get('/ask-foli/api/'+path).status_code,401,path)

    @patch('dashboard.foli_views.foli_api.call')
    def test_private_page_and_api_refuse_remote_or_receiver_context(self,call):
        for path in ('/ask-foli/','/ask-foli/api/documents/'):
            self.assertEqual(self.client.get(path,REMOTE_ADDR='203.0.113.99').status_code,404)
        with override_settings(RECEIVER_ONLY=True):
            self.assertEqual(self.client.get('/ask-foli/').status_code,404)
        call.assert_not_called()

    @patch('dashboard.foli_views.foli_api.call',return_value=([{'id':DOC,'name':'<script>private</script>'}],200))
    def test_proxy_uses_only_authenticated_session_and_preserves_text_data(self,call):
        response=self.client.get('/ask-foli/api/documents/')
        self.assertEqual(response.json()[0]['name'],'<script>private</script>')
        call.assert_called_once_with('GET','documents',['synthetic-holder','test-only-secret'])

    @patch('dashboard.foli_views.foli_api.call',return_value=({'id':JOB,'state':'QUEUED'},202))
    def test_jobs_require_real_csrf_and_valid_json(self,call):
        client=Client(enforce_csrf_checks=True)
        session=client.session; session['sb_auth']=['h','p']; session.save()
        payload={'question':'Read this strange but harmless question','mode':'chat','history':[]}
        self.assertEqual(client.post('/ask-foli/api/jobs/',data=json.dumps(payload),content_type='application/json').status_code,403)
        client.get('/ask-foli/')
        token=client.cookies['csrftoken'].value
        self.assertEqual(client.post('/ask-foli/api/jobs/',data=json.dumps(payload),content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,202)
        self.assertEqual(client.post('/ask-foli/api/jobs/',data='{}',content_type='application/json',HTTP_X_CSRFTOKEN=token,HTTP_ORIGIN='https://evil.invalid').status_code,403)
        self.assertEqual(self.client.post('/ask-foli/api/jobs/',data='not JSON',content_type='application/json').status_code,400)
        self.assertEqual(self.client.post('/ask-foli/api/jobs/',data='x'*32769,content_type='application/json').status_code,413)
        self.assertEqual(self.client.post('/ask-foli/api/jobs/',data='{"url":"https://evil.invalid"}',content_type='application/json').status_code,400)
        self.assertEqual(call.call_count,1)

    @patch('dashboard.foli_views.foli_api.call',return_value=({'forgotten':True},200))
    def test_source_params_are_typed_and_cannot_supply_urls(self,call):
        params={'documentId':DOC,'hash':HASH,'page':'125'}
        self.assertEqual(self.client.get('/ask-foli/api/source/',params).status_code,200)
        for key,value in [('documentId','../../private.key'),('hash','invalid'),('page','0'),('page','5001')]:
            self.assertEqual(self.client.get('/ask-foli/api/source/',params|{key:value}).status_code,400)
        self.assertEqual(self.client.get('/ask-foli/api/source/',params|{'url':'https://evil.invalid'}).status_code,400)
        self.assertEqual(call.call_count,1)

    @patch('dashboard.foli_views.foli_api.call',return_value=(b'\x89PNG\r\n\x1a\n',200))
    def test_png_job_cancel_and_forget_routes_remain_private(self,call):
        self.assertEqual(self.client.get('/ask-foli/api/page/',{'documentId':DOC,'hash':HASH,'page':'1'})['Content-Type'],'image/png')
        call.return_value=({'state':'CANCELLED'},200)
        self.assertEqual(self.client.delete('/ask-foli/api/jobs/'+JOB+'/').status_code,200)
        self.assertEqual(self.client.delete('/ask-foli/api/memory/').status_code,200)
        self.assertEqual(self.client.get('/ask-foli/api/memory/').status_code,405)
        self.assertEqual(self.client.get('/ask-foli/api/jobs/not-an-id/').status_code,404)

    @patch('dashboard.foli_views.foli_api.call',side_effect=foli_api.FoliAPIError('MODEL_MISSING','Install local model.',503))
    def test_unavailability_has_clear_safe_error(self,call):
        response=self.client.get('/ask-foli/api/health/')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json(),{'code':'MODEL_MISSING','message':'Install local model.'})


@override_settings(**PROFILE)
class FoliReceiverTests(TestCase):
    def test_every_foli_route_and_asset_is_absent_from_receiver(self):
        for path in ('/ask-foli/','/ask-foli/api/documents/','/ask-foli/api/jobs/',
                     '/ask-foli/api/source/','/ask-foli/api/page/','/api/foli/health','/api/foli/documents',
                     '/api/foli/jobs/'+JOB,'/static/wallet/foli.css','/static/wallet/foli.js',
                     '/ollama/','/api/chat','/api/tags'):
            for method in ('get','post'):
                response=getattr(self.client,method)(path,secure=True,HTTP_HOST=HOST)
                self.assertEqual(response.status_code,405 if method=='post' and path.startswith('/static/') else 404,(method,path))


class FoliProxyTests(SimpleTestCase):
    @override_settings(SPRING_BOOT_API_BASE_URL='http://localhost:8080')
    def test_config_normalizes_localhost_without_dns(self):
        self.assertEqual(foli_api.origin(),'http://127.0.0.1:8080')
        for value in ('https://127.0.0.1:8080','http://evil.invalid:8080','http://127.0.0.1:8080/redirect','http://u:p@127.0.0.1:8080'):
            with override_settings(SPRING_BOOT_API_BASE_URL=value):
                with self.assertRaises(foli_api.FoliAPIError): foli_api.origin()

    @patch('dashboard.foli_api.requests.Session')
    def test_transport_disables_proxies_redirects_and_has_no_fallback(self,session):
        client=session.return_value.__enter__.return_value
        response=client.request.return_value.__enter__.return_value
        response.status_code=200; response.iter_content.return_value=[b'{"status":"READY"}']
        self.assertEqual(foli_api.call('GET','health',['holder','private'])[0]['status'],'READY')
        self.assertFalse(client.trust_env)
        args,kwargs=client.request.call_args
        self.assertEqual(args[:2],('GET','http://127.0.0.1:8080/api/foli/health'))
        self.assertFalse(kwargs['allow_redirects']); self.assertEqual(kwargs['auth'],('holder','private'))
        for path in ('../api/wallet/documents','https://evil.invalid','jobs/../../file'):
            with self.assertRaises(foli_api.FoliAPIError): foli_api.call('GET',path,['holder','private'])
        with self.assertRaises(foli_api.FoliAPIError): foli_api.call('GET','health',None)

    @patch('dashboard.foli_api.requests.Session')
    def test_redirects_huge_results_and_fake_png_are_rejected(self,session):
        response=session.return_value.__enter__.return_value.request.return_value.__enter__.return_value
        response.status_code=302; response.iter_content.return_value=[b'']
        with self.assertRaises(foli_api.FoliAPIError): foli_api.call('GET','health',['h','p'])
        response.status_code=200; response.iter_content.return_value=[b'x'*(8*1024*1024+1)]
        with self.assertRaises(foli_api.FoliAPIError): foli_api.call('GET','health',['h','p'])
        response.iter_content.return_value=[b'<script>alert(1)</script>']; response.headers={'Content-Type':'text/html'}
        with self.assertRaises(foli_api.FoliAPIError): foli_api.call('GET','page',['h','p'],image=True)

    def test_access_log_filter_removes_foli_paths_and_does_not_emit_body(self):
        filter=ReceiverRequestLogFilter()
        for message in ('GET /ask-foli/','GET /ask-foli/api/jobs/'+JOB+'/','POST /ask-foli/api/jobs/'):
            self.assertFalse(filter.filter(logging.LogRecord('django.server',20,'',0,message,(),None)))
        self.assertTrue(filter.filter(logging.LogRecord('django.server',20,'',0,'GET /health/',(),None)))
