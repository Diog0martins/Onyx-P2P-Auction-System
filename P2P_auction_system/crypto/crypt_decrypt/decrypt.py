from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import base64
import json

def decrypt_message_symmetric(payload_json: str, key: bytes) -> str:
    """
    payload_json: string JSON con "iv" y "ciphertext"
    key: bytes de 32 bytes (AES-256)
    """
    data = json.loads(payload_json)
    iv = base64.b64decode(data["iv"])
    ciphertext = base64.b64decode(data["ciphertext"])

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Quitar padding
    padding_len = padded[-1]
    message = padded[:-padding_len].decode()
    return message

