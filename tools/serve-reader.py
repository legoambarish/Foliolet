"""Loopback-only independent reader with an explicit static allowlist."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit
root = Path(__file__).resolve().parent.parent
class Reader(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        name = unquote(urlsplit(path).path)
        base = root / ('django-service/dashboard/static/wallet' if name.startswith('/vendor/') else 'reader')
        relative = name[len('/vendor/'):] if name.startswith('/vendor/') else name.lstrip('/') or 'index.html'
        target = (base / relative).resolve()
        return str(target) if target.is_relative_to(base.resolve()) else str(base / '__denied__')
    def list_directory(self, path):
        self.send_error(404)
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' http://127.0.0.1:8545 http://localhost:8545; frame-ancestors 'none'")
        super().end_headers()
print('Independent reader on http://127.0.0.1:8090', flush=True)
ThreadingHTTPServer(('127.0.0.1', 8090), Reader).serve_forever()
