"""
Тесты для криптографических утилит.
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
    """Тесты для XOR шифрования."""

    def test_xor_encrypt_basic(self):
        """Базовый тест шифрования."""
        data = b"Hello, World!"
        key = "test_key_12345"

        encrypted = xor_encrypt(data, key)

        # Результат должен отличаться от оригинала
        assert encrypted != data
        assert len(encrypted) == len(data)

    def test_xor_decrypt_symmetric(self):
        """Тест симметричности XOR (шифрование = расшифрование)."""
        data = b"Secret message"
        key = "my_secret_key"

        encrypted = xor_encrypt(data, key)
        decrypted = xor_decrypt(encrypted, key)

        assert decrypted == data

    def test_xor_encrypt_empty_data(self):
        """Шифрование пустых данных."""
        data = b""
        key = "test_key"

        encrypted = xor_encrypt(data, key)
        assert encrypted == b""

    def test_xor_encrypt_short_key(self):
        """Шифрование с коротким ключом (меньше данных)."""
        data = b"Long message that is longer than key"
        key = "short_key"  # 9 символов, больше минимума 8

        encrypted = xor_encrypt(data, key)
        decrypted = xor_decrypt(encrypted, key)

        assert decrypted == data

    def test_xor_encrypt_invalid_key_too_short(self):
        """Шифрование с слишком коротким ключом."""
        data = b"Test data"
        key = "short"  # 5 символов, минимум 8

        # Ключ меньше минимальной длины
        with pytest.raises(InvalidKeyError):
            xor_encrypt(data, key)

    def test_xor_encrypt_data_too_large(self):
        """Шифрование слишком больших данных."""
        data = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
        key = "valid_key_123"

        with pytest.raises(DataTooLargeError):
            xor_encrypt(data, key)


class TestEncryptAndEncode:
    """Тесты для encrypt_and_encode."""

    def test_encrypt_and_encode_basic(self):
        """Базовый тест шифрования с кодированием."""
        data = b"Test message"
        key = "encryption_key_123"

        result = encrypt_and_encode(data, key)

        # Результат должен быть base64 строкой
        assert isinstance(result, str)
        assert result.isascii()

    def test_encrypt_and_encode_roundtrip(self):
        """Тест полного цикла (шифрование + расшифрование)."""
        data = b"Round trip test"
        key = "round_trip_key_123"

        encoded = encrypt_and_encode(data, key)
        decoded = decode_and_decrypt(encoded, key)

        assert decoded == data

    def test_encrypt_and_encode_invalid_base64(self):
        """Расшифрование невалидного base64."""
        with pytest.raises(CryptoError):
            decode_and_decrypt("!!!invalid_base64!!!", "key")


class TestVerifyHmacSignature:
    """Тесты для HMAC верификации."""

    def test_verify_valid_signature(self):
        """Верификация валидной подписи."""
        import hmac
        import hashlib

        body = b'{"test": "data"}'
        secret = "super_secret_key"

        # Создаём правильную подпись
        expected_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        result = verify_hmac_signature(body, expected_signature, secret)
        assert result is True

    def test_verify_invalid_signature(self):
        """Верификация невалидной подписи."""
        body = b'{"test": "data"}'
        secret = "super_secret_key"

        result = verify_hmac_signature(body, "wrong_signature", secret)
        assert result is False

    def test_verify_empty_signature(self):
        """Верификация с пустой подписью."""
        body = b'{"test": "data"}'
        secret = "super_secret_key"

        result = verify_hmac_signature(body, "", secret)
        assert result is False

    def test_verify_tampered_body(self):
        """Верификация с изменённым телом."""
        import hmac
        import hashlib

        body = b'{"test": "data"}'
        tampered_body = b'{"test": "tampered"}'
        secret = "super_secret_key"

        # Создаём подпись для оригинального тела
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        # Проверяем с изменённым телом
        result = verify_hmac_signature(tampered_body, signature, secret)
        assert result is False

    def test_verify_unicode_content(self):
        """Верификация с unicode содержимым."""
        import hmac
        import hashlib

        body = "Привет мир! 🌍".encode("utf-8")
        secret = "secret_key"

        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        result = verify_hmac_signature(body, signature, secret)
        assert result is True
