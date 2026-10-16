"""Private HTTP WSGI server; built-in Django static handler, no CDN or dev server."""
import os
import subprocess
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hermes.settings')
sys.path.insert(0, '/app/django-service')
subprocess.run([sys.executable, '/app/django-service/manage.py', 'migrate', '--noinput'], check=True)
from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler
from waitress import serve
serve(StaticFilesHandler(get_wsgi_application()), host='127.0.0.1', port=8000,
      threads=8, max_request_body_size=22*1024*1024, clear_untrusted_proxy_headers=True)
