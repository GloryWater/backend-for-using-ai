"""
Tests for cryptographic utilities.
"""

import pytest

from src.utils.crypto import (
    CryptoError,
    DataTooLargeError,
    InvalidKeyError,
    decode_and_decrypt,
    encrypt_and_encode,
    verify_hmac_signature,
    xor_decrypt,
    xor_encrypt,
)


class TestXorEncrypt:
    """Tests for XOR encryption."""

    def test_xor_encrypt_basic(self):
        """Basic encryption test."""
        data = b"Hello, World!"
        key = "test_key_12345"

        encrypted = xor_encrypt(data, key)

        # Result must differ from original
        assert encrypted != data
        assert len(encrypted) == len(data)

    def test_xor_decrypt_symmetric(self):
        """XOR symmetry test (encryption = decryption)."""
        data = b"Secret message"
        key = "my_secret_key"

        encrypted = xor_encrypt(data, key)
        decrypted = xor_decrypt(encrypted, key)

        assert decrypted == data

    def test_xor_encrypt_empty_data(self):
        """Encrypting empty data."""
        data = b""
        key = "test_key"

        encrypted = xor_encrypt(data, key)
        assert encrypted == b""

    def test_xor_encrypt_short_key(self):
        """Encryption with short key (less than data)."""
        data = b"Long message that is longer than key"
        key = "short_key"  # 9 characters, more than minimum 8

        encrypted = xor_encrypt(data, key)
        decrypted = xor_decrypt(encrypted, key)

        assert decrypted == data

    def test_xor_encrypt_invalid_key_too_short(self):
        """Encryption with too short key."""
        data = b"Test data"
        key = "short"  # 5 characters, minimum 8

        # Key is less than minimum length
        with pytest.raises(InvalidKeyError):
            xor_encrypt(data, key)

    def test_xor_encrypt_data_too_large(self):
        """Encrypting too large data."""
        data = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
        key = "valid_key_123"

        with pytest.raises(DataTooLargeError):
            xor_encrypt(data, key)


class TestEncryptAndEncode:
    """Tests for encrypt_and_encode."""

    def test_encrypt_and_encode_basic(self):
        """Basic encryption with encoding test."""
        data = b"Test message"
        key = "encryption_key_123"

        result = encrypt_and_encode(data, key)

        # Result must be a base64 string
        assert isinstance(result, str)
        assert result.isascii()

    def test_encrypt_and_encode_roundtrip(self):
        """Full cycle test (encryption + decryption)."""
        data = b"Round trip test"
        key = "round_trip_key_123"

        encoded = encrypt_and_encode(data, key)
        decoded = decode_and_decrypt(encoded, key)

        assert decoded == data

    def test_encrypt_and_encode_invalid_base64(self):
        """Decryption of invalid base64."""
        with pytest.raises(CryptoError):
            decode_and_decrypt("!!!invalid_base64!!!", "key")


class TestVerifyHmacSignature:
    """Tests for HMAC verification."""

    def test_verify_valid_signature(self):
        """Valid signature verification."""
        import hmac
        import hashlib

        body = b'{"test": "data"}'
        secret = "super_secret_key"

        # Create correct signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        result = verify_hmac_signature(body, expected_signature, secret)
        assert result is True

    def test_verify_invalid_signature(self):
        """Invalid signature verification."""
        body = b'{"test": "data"}'
        secret = "super_secret_key"

        result = verify_hmac_signature(body, "wrong_signature", secret)
        assert result is False

    def test_verify_empty_signature(self):
        """Verification with empty signature."""
        body = b'{"test": "data"}'
        secret = "super_secret_key"

        result = verify_hmac_signature(body, "", secret)
        assert result is False

    def test_verify_tampered_body(self):
        """Verification with tampered body."""
        import hmac
        import hashlib

        body = b'{"test": "data"}'
        tampered_body = b'{"test": "tampered"}'
        secret = "super_secret_key"

        # Create signature for original body
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        # Verify with tampered body
        result = verify_hmac_signature(tampered_body, signature, secret)
        assert result is False

    def test_verify_unicode_content(self):
        """Verification with unicode content."""
        import hmac
        import hashlib

        body = "Привет мир! 🌍".encode("utf-8")
        secret = "secret_key"

        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        result = verify_hmac_signature(body, signature, secret)
        assert result is True
