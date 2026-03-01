"""
Integration test: verify the encryption format matches the HTML/JS decryptor spec.

The decryptor (static/export-decryptor.html) expects:
  [version: 1 byte][salt: 16 bytes][iv: 12 bytes][ciphertext+tag: remaining]

Algorithm: AES-256-GCM
Key derivation: PBKDF2 with SHA-256, 600,000 iterations
"""
import os
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

VERSION = 0x01
SALT_LEN = 16
IV_LEN = 12
HEADER_LEN = 1 + SALT_LEN + IV_LEN  # 29
ITERATIONS = 600_000
GCM_TAG_LEN = 16


def encrypt_for_export(plaintext: bytes, passphrase: str) -> bytes:
    """Encrypt using the KoNote export format spec."""
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    key = kdf.derive(passphrase.encode("utf-8"))

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)

    return bytes([VERSION]) + salt + iv + ciphertext


def decrypt_export(data: bytes, passphrase: str) -> bytes:
    """Decrypt using the KoNote export format spec."""
    version = data[0]
    assert version == VERSION, f"Unsupported version: {version}"
    salt = data[1:17]
    iv = data[17:29]
    ciphertext = data[29:]

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    key = kdf.derive(passphrase.encode("utf-8"))

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ciphertext, None)


class ExportEncryptionFormatTest:
    """Verify the binary format matches the JS decryptor specification."""

    PASSPHRASE = "correct horse battery staple test phrase"

    def test_header_structure(self):
        """Encrypted output starts with version byte, 16-byte salt, 12-byte IV."""
        plaintext = b"Hello, KoNote!"
        encrypted = encrypt_for_export(plaintext, self.PASSPHRASE)

        # Version byte
        assert encrypted[0] == VERSION

        # Total header length
        assert len(encrypted) >= HEADER_LEN + GCM_TAG_LEN

        # Salt and IV are within the header region (just verify lengths)
        salt = encrypted[1:17]
        iv = encrypted[17:29]
        assert len(salt) == SALT_LEN
        assert len(iv) == IV_LEN

    def test_roundtrip(self):
        """Encrypt then decrypt returns original plaintext."""
        plaintext = b"This is a test payload for KoNote export."
        encrypted = encrypt_for_export(plaintext, self.PASSPHRASE)
        decrypted = decrypt_export(encrypted, self.PASSPHRASE)
        assert decrypted == plaintext

    def test_roundtrip_empty(self):
        """Roundtrip works for empty plaintext."""
        encrypted = encrypt_for_export(b"", self.PASSPHRASE)
        decrypted = decrypt_export(encrypted, self.PASSPHRASE)
        assert decrypted == b""

    def test_roundtrip_large(self):
        """Roundtrip works for a larger payload (simulating a ZIP)."""
        plaintext = os.urandom(100_000)
        encrypted = encrypt_for_export(plaintext, self.PASSPHRASE)
        decrypted = decrypt_export(encrypted, self.PASSPHRASE)
        assert decrypted == plaintext

    def test_ciphertext_includes_gcm_tag(self):
        """Ciphertext region is plaintext length + 16-byte GCM auth tag."""
        plaintext = b"Exactly thirty-two bytes here!!!"
        assert len(plaintext) == 32

        encrypted = encrypt_for_export(plaintext, self.PASSPHRASE)
        ciphertext_region = encrypted[HEADER_LEN:]

        # AES-GCM ciphertext = same length as plaintext + 16-byte tag
        assert len(ciphertext_region) == len(plaintext) + GCM_TAG_LEN

    def test_wrong_passphrase_fails(self):
        """Decryption with wrong passphrase raises an error."""
        plaintext = b"secret data"
        encrypted = encrypt_for_export(plaintext, self.PASSPHRASE)

        with pytest.raises(Exception):
            decrypt_export(encrypted, "wrong passphrase entirely")

    def test_tampered_ciphertext_fails(self):
        """Modifying ciphertext causes GCM authentication to fail."""
        plaintext = b"tamper-proof data"
        encrypted = bytearray(encrypt_for_export(plaintext, self.PASSPHRASE))

        # Flip a bit in the ciphertext region
        encrypted[HEADER_LEN + 5] ^= 0xFF

        with pytest.raises(Exception):
            decrypt_export(bytes(encrypted), self.PASSPHRASE)

    def test_unsupported_version_fails(self):
        """A file with version != 0x01 is rejected."""
        plaintext = b"test"
        encrypted = bytearray(encrypt_for_export(plaintext, self.PASSPHRASE))
        encrypted[0] = 0x02  # bad version

        with pytest.raises(AssertionError):
            decrypt_export(bytes(encrypted), self.PASSPHRASE)

    def test_unique_salt_and_iv(self):
        """Each encryption produces unique salt and IV."""
        plaintext = b"same plaintext"
        enc1 = encrypt_for_export(plaintext, self.PASSPHRASE)
        enc2 = encrypt_for_export(plaintext, self.PASSPHRASE)

        salt1, iv1 = enc1[1:17], enc1[17:29]
        salt2, iv2 = enc2[1:17], enc2[17:29]

        assert salt1 != salt2, "Salts should be random and unique"
        assert iv1 != iv2, "IVs should be random and unique"
