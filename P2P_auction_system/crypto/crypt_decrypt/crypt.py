import os
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes # Não usado diretamente para GCM, mas útil para funções de chave
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def encrypt_message_symmetric_gcm(message: str, key: bytes) -> str:
    """
    message: string a cifrar
    key: bytes de 32 bytes (AES-256)
    """
    # 1. Generate random nonce (AES-GCM uses 12 bytes by default)
    # The nonce MUST be unique for each encryption with the same key.
    nonce = os.urandom(12)

    # 2. Configure the cipher with AES-256 and GCM mode
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()

    # Authenticated Additional Data (AAD). Optional, but good practice.
    # In this case, we use empty AAD, but it is authenticated along with the message.
    aad = b""
    encryptor.authenticate_additional_data(aad)

    # 3. Encrypt the message (without padding)
    ciphertext = encryptor.update(message.encode()) + encryptor.finalize()

    # 4. Obtain the GCM authentication tag
    tag = encryptor.tag

    # 5. Create JSON with Nonce + ciphertext + tag
    payload = {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "tag": base64.b64encode(tag).decode()
    }
    return json.dumps(payload)

def encrypt_with_public_key(message_bytes: bytes, public_key_pem: bytes) -> bytes:
    """
    Encrypts data using an RSA public key (PEM).
    
    message_bytes: Data to be encrypted (must be short for RSA).
    public_key_pem: Recipient's (Seller's) public key in PEM format.
    """
    # Upload the PEM public key
    public_key = serialization.load_pem_public_key(public_key_pem)

    if not isinstance(public_key, rsa.RSAPublicKey):
        raise TypeError("The loaded key is not an RSA public key.")

    # Encrypt using OAEP (Optimal Asymmetric Encryption Padding)
    ciphertext = public_key.encrypt(
        message_bytes,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

