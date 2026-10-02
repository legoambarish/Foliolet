"""Encrypt only already released presentations in the bounded server-side export session."""
import base64
import hashlib
import json
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from django.conf import settings


def cipher(grant_id, nonce):
    key = hashlib.sha256(("proof-export-v1:" + settings.SECRET_KEY).encode()).digest()
    aes = AES.new(key, AES.MODE_GCM, nonce=nonce)
    aes.update(("released-proof-v1:" + grant_id).encode())
    return aes


def seal(bundle):
    nonce = get_random_bytes(12)
    aes = cipher(bundle["presentation"]["grantId"], nonce)
    ciphertext, tag = aes.encrypt_and_digest(json.dumps(bundle).encode())
    return base64.b64encode(nonce + tag + ciphertext).decode()


def open_proof(grant_id, sealed):
    data = base64.b64decode(sealed, validate=True)
    raw = cipher(grant_id, data[:12]).decrypt_and_verify(data[28:], data[12:28])
    return json.loads(raw)
