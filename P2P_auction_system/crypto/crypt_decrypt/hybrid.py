import json
import base64
import os
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def b64e(b: bytes) -> str: 
    """Helper: Encodes bytes to a Base64 ASCII string."""
    return base64.b64encode(b).decode("ascii")

def b64d(s: str) -> bytes: 
    """Helper: Decodes a Base64 ASCII string back to bytes."""
    return base64.b64decode(s.encode("ascii"))

def hybrid_encrypt(data_dict: dict, public_key_pem: bytes) -> str:
    """
    Performs hybrid encryption: Encrypts data with AES-GCM and encrypts the AES key with RSA.

    Args:
        data_dict (dict): The actual data to be protected.
        public_key_pem (bytes): The recipient's RSA public key (PEM format).

    Returns:
        str: A JSON string containing the encrypted AES key, nonce, tag, and ciphertext.
    """
    # Serialize the dictionary to a JSON byte stream
    json_str = json.dumps(data_dict)
    data_bytes = json_str.encode('utf-8')

    # Generate a random 256-bit symmetric key and a standard 96-bit nonce for AES-GCM
    aes_key = os.urandom(32)
    nonce = os.urandom(12)

    # Encrypt the data using AES in Galois/Counter Mode (GCM).
    # GCM provides both confidentiality and integrity (via the tag).
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data_bytes) + encryptor.finalize()
    tag = encryptor.tag

    # Load the recipient's RSA public key
    rsa_pub = serialization.load_pem_public_key(public_key_pem)

    # Encrypt the symmetric AES key using RSA with OAEP padding.
    # This allows the recipient to retrieve the AES key using their private key.
    encrypted_aes_key = rsa_pub.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Package all components needed for decryption into a transportable format
    payload = {
        "enc_aes_key": b64e(encrypted_aes_key),
        "nonce": b64e(nonce),
        "tag": b64e(tag),
        "ciphertext": b64e(ciphertext)
    }

    return json.dumps(payload)


def hybrid_decrypt(payload_json: str, private_key) -> Any | None:
    """
    Performs hybrid decryption: Decrypts the AES key with RSA, then decrypts the data with AES-GCM.

    Args:
        payload_json (str): The JSON output from hybrid_encrypt.
        private_key: The recipient's RSA private key object.

    Returns:
        Any | None: The original data dictionary if successful, or None on failure.
    """
    try:
        # Parse the wrapper to get the Base64 components
        wrapper = json.loads(payload_json)

        # 1. Recover the symmetric AES key
        # Decrypt the encrypted AES key using the RSA private key
        enc_aes_key = b64d(wrapper["enc_aes_key"])
        aes_key = private_key.decrypt(
            enc_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 2. Decrypt the actual payload
        nonce = b64d(wrapper["nonce"])
        tag = b64d(wrapper["tag"])
        ciphertext = b64d(wrapper["ciphertext"])

        # Initialize AES-GCM with the recovered key and the authentication tag.
        # If the tag does not match the data (indicating tampering), this will raise an exception.
        cipher = Cipher(algorithms.AES(aes_key), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Deserialize the JSON bytes back to the original object
        return json.loads(plaintext.decode('utf-8'))

    except Exception as e:
        # Log the specific error for debugging but return None to the caller
        print(f"Hybrid decryption error: {e}")
        return None