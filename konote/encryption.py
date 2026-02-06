"""
Application-level PII encryption using Fernet (AES-128-CBC + HMAC-SHA256).

Supports key rotation via MultiFernet. Set FIELD_ENCRYPTION_KEY to a
comma-separated list of keys — the first key encrypts new data, all keys
can decrypt existing data.

    # Single key (normal operation):
    FIELD_ENCRYPTION_KEY="tFE8M4TjWq..."

    # Key rotation (new key first, old key second):
    FIELD_ENCRYPTION_KEY="newKeyABC...,oldKeyXYZ..."

Usage in models:
    from konote.encryption import encrypt_field, decrypt_field

    class MyModel(models.Model):
        _name_encrypted = models.BinaryField()

        @property
        def name(self):
            return decrypt_field(self._name_encrypted)

        @name.setter
        def name(self, value):
            self._name_encrypted = encrypt_field(value)
"""
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    """Lazy-initialise the Fernet cipher from the configured key(s).

    Supports comma-separated keys for rotation. The first key is used
    for encryption; all keys are tried for decryption.
    """
    global _fernet
    if _fernet is None:
        key_string = settings.FIELD_ENCRYPTION_KEY
        if not key_string:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        keys = [k.strip() for k in key_string.split(",") if k.strip()]
        fernet_instances = [
            Fernet(k.encode() if isinstance(k, str) else k) for k in keys
        ]
        if len(fernet_instances) == 1:
            _fernet = fernet_instances[0]
        else:
            _fernet = MultiFernet(fernet_instances)
    return _fernet


def encrypt_field(plaintext):
    """Encrypt a string value. Returns bytes for storage in BinaryField."""
    if plaintext is None or plaintext == "":
        return b""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_field(ciphertext):
    """Decrypt a BinaryField value back to string."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    try:
        if isinstance(ciphertext, memoryview):
            ciphertext = bytes(ciphertext)
        return f.decrypt(ciphertext).decode("utf-8")
    except InvalidToken:
        logger.error("Decryption failed — possible key mismatch or data corruption")
        return ""


def generate_key():
    """Generate a new Fernet key for initial setup."""
    return Fernet.generate_key().decode()
