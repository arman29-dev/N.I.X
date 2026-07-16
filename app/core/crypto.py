import os
import json
import base64
import hmac
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(secret: str, salt: str = "nix-desktop-registration") -> bytes:
    return hmac.new(secret.encode("utf-8"), salt.encode("utf-8"), hashlib.sha256).digest()


def encrypt_config(payload: dict, secret: str) -> str:
    key = _derive_key(secret)
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    data = json.dumps(payload).encode("utf-8")
    ct = aesgcm.encrypt(iv, data, None)
    return json.dumps({
        "data": base64.b64encode(ct).decode("utf-8"),
        "iv": base64.b64encode(iv).decode("utf-8"),
    })


def decrypt_config(encrypted: str, secret: str) -> dict:
    key = _derive_key(secret)
    aesgcm = AESGCM(key)
    blob = json.loads(encrypted)
    ct = base64.b64decode(blob["data"])
    iv = base64.b64decode(blob["iv"])
    data = aesgcm.decrypt(iv, ct, None)
    return json.loads(data)
