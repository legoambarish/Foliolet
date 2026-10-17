"""Encrypt JSON inside Django's existing authenticated session envelope.

The browser still receives only a random database session identifier. This protects
session database copies that do not include the Django key; the backend remains
custodial and a compromised host/key is not protected. Legacy signed JSON is read
for compatibility and can be rewritten with `reencrypt_sessions`.
"""
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.Random import get_random_bytes
from django.conf import settings
from django.core.signing import JSONSerializer

PREFIX = b'FSES1:'
CONTEXT = b'foliolet:database-session:encryption:v1'
MAX_BYTES = 2 * 1024 * 1024


def key(secret):
    return HKDF(secret.encode('utf-8'), 32, b'foliolet-session-key-v1', SHA256, context=CONTEXT)


class EncryptedJSONSerializer:
    def dumps(self, obj):
        raw = JSONSerializer().dumps(obj)
        if len(raw) > MAX_BYTES:
            raise ValueError('Private session exceeds the supported size limit')
        nonce = get_random_bytes(12)
        cipher = AES.new(key(settings.SECRET_KEY), AES.MODE_GCM, nonce=nonce)
        cipher.update(CONTEXT)
        ciphertext, tag = cipher.encrypt_and_digest(raw)
        return PREFIX + nonce + tag + ciphertext

    def loads(self, data):
        if not isinstance(data, bytes) or len(data) > MAX_BYTES + len(PREFIX) + 28:
            raise ValueError('Invalid private session size')
        if not data.startswith(PREFIX):
            # Django checks its outer signature before invoking this deserializer.
            # This path is deliberately JSON-only: no pickle or arbitrary objects.
            return JSONSerializer().loads(data)
        payload = data[len(PREFIX):]
        if len(payload) < 28:
            raise ValueError('Invalid private session envelope')
        for secret in (settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS):
            try:
                cipher = AES.new(key(secret), AES.MODE_GCM, nonce=payload[:12])
                cipher.update(CONTEXT)
                plain = cipher.decrypt_and_verify(payload[28:], payload[12:28])
                return JSONSerializer().loads(plain)
            except ValueError:
                continue
        raise ValueError('Private session failed authentication')
