from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.http import HttpResponse
from django.test import SimpleTestCase
from dashboard.wallet_views import enroll


class UploadLimitTests(SimpleTestCase):
    def request(self, size, body):
        file = SimpleNamespace(size=size, read=Mock(return_value=body), name='fictional.pdf', content_type='application/pdf')
        return SimpleNamespace(method='POST', FILES={'file':file}, POST={}, session={'sb_auth':['fictional-holder','fictional-password']}), file

    @patch('dashboard.wallet_views.page', return_value=HttpResponse())
    @patch('dashboard.wallet_views.api.call', return_value=[])
    def test_declared_oversize_is_rejected_before_read(self, api, page):
        request, file = self.request(20*1024*1024+1, b'')
        enroll(request)
        file.read.assert_not_called()
        self.assertIn('20 MiB', page.call_args.kwargs['error'])
        self.assertTrue(all(call.args[0]=='GET' for call in api.call_args_list))

    @patch('dashboard.wallet_views.page', return_value=HttpResponse())
    @patch('dashboard.wallet_views.api.call', return_value=[])
    def test_false_size_metadata_cannot_bypass_the_bounded_read(self, api, page):
        request, file = self.request(1, b'x'*(20*1024*1024+1))
        enroll(request)
        file.read.assert_called_once_with(20*1024*1024+1)
        self.assertIn('20 MiB', page.call_args.kwargs['error'])
        self.assertTrue(all(call.args[0]=='GET' for call in api.call_args_list))

    @patch('dashboard.wallet_views.api.call', side_effect=[[], {'id':'fictional-id'}])
    def test_supported_original_bytes_are_forwarded_unchanged(self, api):
        original=b'%PDF-fictional-exact-original'
        request, file = self.request(len(original),original)
        response=enroll(request)
        self.assertEqual(response.status_code,302)
        self.assertEqual(api.call_args.kwargs['files']['file'][1],original)
        file.read.assert_called_once_with(20*1024*1024+1)
