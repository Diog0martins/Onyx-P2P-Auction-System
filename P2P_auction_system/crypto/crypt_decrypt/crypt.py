from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import base64
import json

def encrypt_message_symmetric(message: str, key: bytes) -> str:
    """
    message: string a cifrar
    key: bytes de 32 bytes (AES-256)
    """
    # Generar IV aleatorio
    iv = os.urandom(16)

    # Padding PKCS7 manual
    padding_len = 16 - (len(message) % 16)
    padded_message = message + chr(padding_len) * padding_len

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_message.encode()) + encryptor.finalize()

    # Crear JSON con IV + ciphertext
    payload = {
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }
    return json.dumps(payload)

