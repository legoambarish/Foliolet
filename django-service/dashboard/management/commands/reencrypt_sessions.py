"""Rewrite only valid legacy signed JSON; preserve keys, expiry and concurrent changes."""
from importlib import import_module
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import signing
from django.core.management.base import BaseCommand, CommandError
from dashboard.private_sessions import PREFIX, EncryptedJSONSerializer


class RawSerializer:
    def loads(self, data): return data


class Command(BaseCommand):
    help = 'Encrypt legacy signed database sessions without replacing session IDs or changing expiry.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Inspect counts without writing any rows.')

    def handle(self, *args, **options):
        if settings.SESSION_SERIALIZER != 'dashboard.private_sessions.EncryptedJSONSerializer':
            raise CommandError('Enable the encrypted JSON serializer before this migration.')
        store = import_module(settings.SESSION_ENGINE).SessionStore()
        counts = dict(already_encrypted=0, pending=0, rewritten=0, invalid=0, concurrent_changes=0)
        for session in Session.objects.all().iterator(chunk_size=100):
            try:
                raw = signing.loads(session.session_data, salt=store.key_salt, serializer=RawSerializer)
                if raw.startswith(PREFIX):
                    EncryptedJSONSerializer().loads(raw)  # Do not silently count corrupt ciphertext as valid.
                    counts['already_encrypted'] += 1
                    continue
                value = signing.JSONSerializer().loads(raw)
                if not isinstance(value, dict): raise ValueError('Session must contain a JSON object')
            except (ValueError, TypeError, signing.BadSignature, UnicodeError):
                counts['invalid'] += 1
                continue
            counts['pending'] += 1
            if options['dry_run']: continue
            changed = Session.objects.filter(session_key=session.session_key, session_data=session.session_data).update(
                session_data=store.encode(value))
            counts['rewritten' if changed else 'concurrent_changes'] += 1
        self.stdout.write(' '.join(f'{name}={number}' for name, number in counts.items()))
