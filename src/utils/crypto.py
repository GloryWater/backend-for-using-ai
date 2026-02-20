"""
Криптографические утилиты.

WARNING: XOR-шифрование используется только для обфускации, не является криптостойким.
Для серьёзной защиты рекомендуется использовать AES-GCM или libsodium.
"""

import base64
import hashlib
import hmac
import logging
from typing import Final

logger = logging.getLogger(__name__)

# Максимальный размер данных для шифрования (защита от DoS)
_MAX_DATA_SIZE: Final[int] = 10 * 1024 * 1024  # 10 MB
# Минимальная длина ключа
_MIN_KEY_LENGTH: Final[int] = 8


class CryptoError(Exception):
    """Базовое исключение для криптографических операций."""


class DataTooLargeError(CryptoError):
    """Превышен максимальный размер данных."""


class InvalidKeyError(CryptoError):
    """Невалидный ключ шифрования."""


def _validate_key(key: str) -> None:
    """Проверяет валидность ключа."""
    if len(key) < _MIN_KEY_LENGTH:
        raise InvalidKeyError(
            f"Key length must be at least {_MIN_KEY_LENGTH} characters, got {len(key)}"
        )
    if not key.encode("utf-8").isascii():
        logger.warning("Non-ASCII characters in encryption key")


def _validate_data_size(data: bytes) -> None:
    """Проверяет размер данных."""
    if len(data) > _MAX_DATA_SIZE:
        raise DataTooLargeError(
            f"Data size {len(data)} bytes exceeds maximum {_MAX_DATA_SIZE} bytes"
        )


def xor_encrypt(data: bytes, key: str) -> bytes:
    """
    XOR-шифрование данных.

    Args:
        data: Данные для шифрования
        key: Ключ шифрования

    Returns:
        Зашифрованные данные

    Raises:
        InvalidKeyError: Если ключ слишком короткий
        DataTooLargeError: Если данные слишком большие
    """
    _validate_key(key)
    _validate_data_size(data)

    key_bytes = key.encode("utf-8")
    return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)])


def xor_decrypt(data: bytes, key: str) -> bytes:
    """
    XOR-расшифрование данных (алгоритм симметричный).

    Args:
        data: Зашифрованные данные
        key: Ключ расшифрования

    Returns:
        Расшифрованные данные
    """
    return xor_encrypt(data, key)  # XOR симметричен


def encrypt_and_encode(data: bytes, key: str) -> str:
    """
    XOR-шифрование + Base64-кодирование для передачи по сети.

    Args:
        data: Данные для шифрования
        key: Ключ шифрования

    Returns:
        Base64-строка с зашифрованными данными

    Raises:
        CryptoError: Ошибка шифрования
    """
    try:
        encrypted = xor_encrypt(data, key)
        return base64.b64encode(encrypted).decode("ascii")
    except CryptoError:
        raise
    except Exception as e:
        logger.exception("Unexpected error during encryption")
        raise CryptoError(f"Encryption failed: {e}") from e


def decode_and_decrypt(encoded_data: str, key: str) -> bytes:
    """
    Base64-декодирование + XOR-расшифрование.

    Args:
        encoded_data: Base64-строка с зашифрованными данными
        key: Ключ расшифрования

    Returns:
        Расшифрованные данные

    Raises:
        CryptoError: Ошибка расшифрования
    """
    try:
        data = base64.b64decode(encoded_data.encode("ascii"))
        return xor_decrypt(data, key)
    except UnicodeDecodeError as e:
        logger.warning("Invalid base64 encoding")
        raise CryptoError(f"Invalid base64: {e}") from e
    except CryptoError:
        raise
    except Exception as e:
        logger.exception("Unexpected error during decryption")
        raise CryptoError(f"Decryption failed: {e}") from e


def verify_hmac_signature(body: bytes, signature: str, secret_key: str) -> bool:
    """
    Проверяет HMAC-SHA256 подпись.

    Args:
        body: Тело запроса
        signature: Полученная подпись (hex string)
        secret_key: Секретный ключ для верификации

    Returns:
        True если подпись валидна
    """
    if not signature:
        return False

    expected = hmac.new(secret_key.encode("utf-8"), body, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected, signature)
