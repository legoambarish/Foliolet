"""Transport boundary tests: no document or credential leaves the local service."""
from unittest.mock import MagicMock, patch
import requests
from django.test import SimpleTestCase, override_settings
from dashboard import wallet_api


@override_settings(SPRING_BOOT_API_BASE_URL='http://localhost:8080')
class WalletTransportTests(SimpleTestCase):
    def client(self, body=b'{"ok":true}', status=200, headers=None):
        patcher = patch('dashboard.wallet_api.requests.Session')
        session_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = session_class.return_value.__enter__.return_value
        response = client.request.return_value.__enter__.return_value
        response.status_code = status
        response.headers = headers or {'Content-Type': 'application/json'}
        response.iter_content.return_value = [body]
        return client, response

    def test_loopback_is_numeric_and_environment_proxies_are_disabled(self):
        client, _ = self.client()
        self.assertEqual(wallet_api.call('GET', '/api/wallet/documents', ['holder', 'private-password']), {'ok': True})
        args, kwargs = client.request.call_args
        self.assertEqual(args[:2], ('GET', 'http://127.0.0.1:8080/api/wallet/documents'))
        self.assertIs(client.trust_env, False)
        self.assertIs(kwargs['allow_redirects'], False)
        self.assertIs(kwargs['stream'], True)
        self.assertEqual(kwargs['auth'], ('holder', 'private-password'))

    def test_redirect_is_refused_without_reading_a_redirect_body(self):
        client, response = self.client(status=307, headers={'Location': 'https://outside.invalid/upload'})
        with self.assertRaises(wallet_api.WalletAPIError):
            wallet_api.call('POST', '/api/wallet/documents', ['holder', 'private-password'], payload={'private': 'document'})
        response.iter_content.assert_not_called()
        self.assertIs(client.request.call_args.kwargs['allow_redirects'], False)

    def test_remote_or_malformed_origin_is_rejected_before_any_request(self):
        for base in ('https://outside.invalid', 'http://127.0.0.1.evil.invalid', 'http://u:p@localhost:8080',
                     'http://localhost:8080/path', 'http://localhost:8080?x=1', 'http://localhost:bad',
                     'http://localhost:8080#x', 'http://local\nhost:8080'):
            with self.subTest(base=base), override_settings(SPRING_BOOT_API_BASE_URL=base):
                with patch('dashboard.wallet_api.requests.Session') as constructor:
                    with self.assertRaises(wallet_api.WalletAPIError):
                        wallet_api.call('GET', '/api/wallet/documents', ['holder', 'secret'])
                    constructor.assert_not_called()

    def test_unsafe_path_is_rejected_before_any_request(self):
        for path in ('https://outside.invalid', '//outside.invalid/api', '/other', '/api/x#fragment', '/api/x\r\nX: y'):
            with self.subTest(path=path), patch('dashboard.wallet_api.requests.Session') as constructor:
                with self.assertRaises(wallet_api.WalletAPIError):
                    wallet_api.call('GET', path, ['holder', 'secret'])
                constructor.assert_not_called()

    def test_json_response_size_is_bounded(self):
        _, response = self.client()
        response.iter_content.return_value = iter([b'x' * 65536] * 129)
        with self.assertRaises(wallet_api.WalletAPIError) as caught:
            wallet_api.call('GET', '/api/wallet/documents', ['holder', 'secret'])
        self.assertIn('limit', str(caught.exception))

    def test_binary_original_is_returned_without_json_coercion(self):
        _, response = self.client(body=b'%PDF-fictional', headers={'Content-Disposition': 'attachment; filename="sample.pdf"'})
        content, disposition = wallet_api.call('GET', '/api/wallet/documents/abc/file', ['holder', 'secret'], binary=True)
        self.assertEqual(content, b'%PDF-fictional')
        self.assertEqual(disposition, 'attachment; filename="sample.pdf"')

    def test_non_json_error_body_is_not_reflected(self):
        self.client(body=b'<script>private-error-secret</script>', status=400)
        with self.assertRaises(wallet_api.WalletAPIError) as caught:
            wallet_api.call('GET', '/api/wallet/documents', ['holder', 'secret'])
        self.assertNotIn('private-error-secret', str(caught.exception))
        self.assertEqual(caught.exception.status, 400)

    def test_offline_is_an_explicit_failure_not_a_verification_success(self):
        client, _ = self.client()
        client.request.side_effect = requests.ConnectionError('internal diagnostic')
        with self.assertRaises(wallet_api.WalletAPIError) as caught:
            wallet_api.call('GET', '/api/public/network')
        self.assertEqual(caught.exception.status, 503)
        self.assertIn('No verification was completed', str(caught.exception))
        self.assertNotIn('internal diagnostic', str(caught.exception))

    def test_invalid_auth_shape_is_not_sent(self):
        with patch('dashboard.wallet_api.requests.Session') as constructor:
            for auth in (['only-one'], ['u', ''], ['u', 123]):
                with self.assertRaises(wallet_api.WalletAPIError):
                    wallet_api.call('GET', '/api/wallet/documents', auth)
            constructor.assert_not_called()
