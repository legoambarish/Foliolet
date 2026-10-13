"""Separate opt-in public process. Private routes and administration are absent."""
from .settings import *
ROOT_URLCONF = 'hermes.public_urls'
DEBUG = False
ALLOWED_HOSTS = os.environ.get('PUBLIC_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
SESSION_COOKIE_NAME = 'foliolet_public_session'
CSRF_COOKIE_NAME = 'foliolet_public_csrf'
SESSION_COOKIE_SECURE = os.environ.get('PUBLIC_LOCAL_HTTP', 'false') != 'true'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_TRUSTED_ORIGINS = [os.environ['PUBLIC_BASE_URL'].rstrip('/')] if os.environ.get('PUBLIC_BASE_URL') else []
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django.contrib.admin']
