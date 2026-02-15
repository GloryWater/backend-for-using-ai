import base64


def xor_encrypt(data: bytes, key: str) -> bytes:
    key_bytes = key.encode("utf-8")
    return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)])


def encrypt_and_encode(data: bytes, key: str) -> str:
    """XOR-шифрование + Base64-кодирование для передачи по сети."""
    return base64.b64encode(xor_encrypt(data, key)).decode("utf-8")
