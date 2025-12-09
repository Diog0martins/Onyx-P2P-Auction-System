import base64
import json

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def decrypt_message_symmetric_gcm(payload_json: str, key: bytes) -> str:
    """
    payload_json: string JSON con "nonce", "ciphertext", y "tag"
    key: bytes de 32 bytes (AES-256)
    """
    data = json.loads(payload_json)

    # 1. Decoding Nonce, Ciphertext, and Tag
    nonce = base64.b64decode(data["nonce"])
    ciphertext = base64.b64decode(data["ciphertext"])
    tag = base64.b64decode(data["tag"]) # The tag is crucial for authentication.

    # 2. Configure the cipher with AES-256 and GCM mode
    # NOTE: In GCM, it is more common (and idiomatic) to use the AESGCM interface, 
    # but to maintain consistency with your use of Cipher/modes, 
    # we will continue with it, even though it is a little more verbose.

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    decryptor = cipher.decryptor()

    # Authenticated Additional Data (AAD). Must be the same as that used in encryption.
    aad = b""
    decryptor.authenticate_additional_data(aad)

    # 3. Decrypt and verify the Tag
    try:
        # The finalize_with_tag call performs decryption AND tag verification.
        plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize_with_tag(tag)
    except InvalidTag:
        # THIS IS THE CRITICAL POINT: if the tag is invalid, the message has been altered.
        raise ValueError("Invalid authentication tag. Data integrity check failed.")

    # 4. Decode and return the message (GCM does not have padding)
    message = plaintext_bytes.decode()
    return message

def decrypt_with_private_key(ciphertext: bytes, private_key_pem: bytes) -> bytes:
    """
    Decrypts data using an RSA private key (PEM).
    
    ciphertext: Encrypted data.
    private_key_pem: Recipient's (Seller's) private key in PEM format.
    """
    # Upload the PEM private key
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None # Assuming that the private key is not password protected
    )

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError("A chave carregada não é uma chave privada RSA.")

    # Decrypt using OAEP, which must match the padding scheme used in encryption.
    plaintext = private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext

