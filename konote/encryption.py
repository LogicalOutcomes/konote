"""
Application-level PII encryption using Fernet (AES-128-CBC + HMAC-SHA256).

Multi-tenancy support:
    In a multi-tenant deployment, each agency has its own Fernet key stored
    in the TenantKey table (shared schema), encrypted by the master
    FIELD_ENCRYPTION_KEY. The per-tenant key is resolved automatically from
    the current tenant context set by django-tenants middleware.

    Fallback: if no TenantKey exists for the current tenant (e.g. during
    migration from single-tenant), the master key is used directly. This
    ensures backward compatibility.

Key rotation:
    Set FIELD_ENCRYPTION_KEY to a comma-separated list of keys — the first
    key encrypts new data, all keys can decrypt existing data.

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
import threading

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.checks import Error, register

logger = logging.getLogger(__name__)

# Master key Fernet (from env var) — used when no tenant key exists.
# Named _fernet (not _master_fernet) for backward compatibility with tests
# that clear the cache via enc_module._fernet = None.
_fernet = None

# Thread-local cache of per-tenant Fernet instances (keyed by schema_name)
_tenant_fernet_cache = threading.local()


class DecryptionError(Exception):
    """Raised when a field cannot be decrypted.

    This typically means the encryption key has changed (key rotation without
    re-encryption) or the stored ciphertext is corrupted. Silent failure is
    NOT acceptable — callers must handle this explicitly.
    """


def _get_master_fernet():
    """Lazy-initialise the master Fernet cipher from the configured key(s).

    The master key encrypts/decrypts tenant keys AND serves as the fallback
    for tenants without their own key (backward compatibility).
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


def _get_current_schema():
    """Get the current tenant schema name, or None if not in tenant context."""
    try:
        from django.db import connection
        schema = getattr(connection, "schema_name", None)
        if schema and schema != "public":
            return schema
    except Exception:
        pass
    return None


def _get_tenant_fernet(schema_name):
    """Get or create a Fernet instance for a specific tenant schema.

    Looks up the tenant's encrypted key in TenantKey, decrypts it using
    the master key, and caches the result per-thread.

    Returns None if no TenantKey exists (caller falls back to master key).
    """
    # Check thread-local cache
    cache = getattr(_tenant_fernet_cache, "cache", None)
    if cache is None:
        cache = {}
        _tenant_fernet_cache.cache = cache

    if schema_name in cache:
        return cache[schema_name]

    # Look up tenant key from shared schema
    try:
        from apps.tenants.models import Agency, TenantKey
        agency = Agency.objects.get(schema_name=schema_name)
        tenant_key = TenantKey.objects.get(tenant=agency)
    except Exception:
        # No TenantKey for this tenant — fall back to master key
        cache[schema_name] = None
        return None

    # Decrypt the tenant key using the master key
    master = _get_master_fernet()
    try:
        encrypted_key = tenant_key.encrypted_key
        if isinstance(encrypted_key, memoryview):
            encrypted_key = bytes(encrypted_key)
        raw_key = master.decrypt(encrypted_key)
        tenant_fernet = Fernet(raw_key)
        cache[schema_name] = tenant_fernet
        return tenant_fernet
    except InvalidToken:
        logger.error(
            "Failed to decrypt tenant key for schema '%s' — master key mismatch",
            schema_name,
        )
        cache[schema_name] = None
        return None


def _get_fernet():
    """Get the appropriate Fernet for the current context.

    In a multi-tenant context: returns the tenant's Fernet if available,
    otherwise falls back to the master key.

    In single-tenant or non-tenant context: returns the master key Fernet.
    """
    schema = _get_current_schema()
    if schema:
        tenant_fernet = _get_tenant_fernet(schema)
        if tenant_fernet is not None:
            return tenant_fernet
    return _get_master_fernet()


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
        raise DecryptionError(
            "Decryption failed — possible key mismatch or data corruption"
        )


def generate_key():
    """Generate a new Fernet key for initial setup."""
    return Fernet.generate_key().decode()


@register()
def check_encryption_key(app_configs, **kwargs):
    """Django system check: verify the master encryption key round-trips correctly.

    Runs on every `./manage.py check` (and on startup). Fails loudly if the
    key is misconfigured, so operators discover the problem at boot time rather
    than when a staff member opens a client record.
    """
    errors = []
    try:
        # Reset the cached master fernet so we pick up the current settings value
        global _fernet
        _fernet = None
        master = _get_master_fernet()
        test_plaintext = b"konote-encryption-selftest"
        ciphertext = master.encrypt(test_plaintext)
        result = master.decrypt(ciphertext)
        if result != test_plaintext:
            errors.append(
                Error(
                    "FIELD_ENCRYPTION_KEY round-trip check failed: "
                    "encrypt then decrypt did not return the original value.",
                    hint="Check that FIELD_ENCRYPTION_KEY is a valid Fernet key.",
                    id="konote.E001",
                )
            )
    except Exception as exc:
        errors.append(
            Error(
                f"FIELD_ENCRYPTION_KEY is invalid or missing: {exc}",
                hint=(
                    "Generate a key with: "
                    "python -c \"from cryptography.fernet import Fernet; "
                    "print(Fernet.generate_key().decode())\""
                ),
                id="konote.E001",
            )
        )
    finally:
        # Leave the cache clean so the first real use re-initialises normally
        _fernet = None
    return errors


def clear_tenant_key_cache():
    """Clear the thread-local tenant key cache.

    Call this after rotating a tenant key to force re-reading from the database.
    """
    _tenant_fernet_cache.cache = {}
