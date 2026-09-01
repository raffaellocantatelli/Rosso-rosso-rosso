"""Firma Ed25519 persistente per nodo (autenticità dei documenti).

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import os

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey

from . import config

_KEY_PATH = os.path.join(config.DATA_DIR, "node_key.seed")
_signing_key = None


def _load_or_create_key():
    global _signing_key
    if _signing_key is not None:
        return _signing_key
    os.makedirs(config.DATA_DIR, exist_ok=True)
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            seed = f.read()
        _signing_key = SigningKey(seed)
    else:
        _signing_key = SigningKey.generate()
        with open(_KEY_PATH, "wb") as f:
            f.write(bytes(_signing_key))
    return _signing_key


def sign(data: bytes) -> str:
    key = _load_or_create_key()
    return key.sign(data).signature.hex()


def verify_key_hex() -> str:
    key = _load_or_create_key()
    return key.verify_key.encode(encoder=HexEncoder).decode()
