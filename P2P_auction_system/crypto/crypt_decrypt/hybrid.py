import json
import base64
import os
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def b64e(b: bytes) -> str: return base64.b64encode(b).decode("ascii")

def b64d(s: str) -> bytes: return base64.b64decode(s.encode("ascii"))

def hybrid_encrypt(data_dict: dict, public_key_pem: bytes) -> str:
    json_str = json.dumps(data_dict)
    data_bytes = json_str.encode('utf-8')
    aes_key = os.urandom(32)
    nonce = os.urandom(12)
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data_bytes) + encryptor.finalize()
    tag = encryptor.tag
    rsa_pub = serialization.load_pem_public_key(public_key_pem)

    encrypted_aes_key = rsa_pub.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    payload = {
        "enc_aes_key": b64e(encrypted_aes_key),
        "nonce": b64e(nonce),
        "tag": b64e(tag),
        "ciphertext": b64e(ciphertext)
    }

    return json.dumps(payload)


def hybrid_decrypt(payload_json: str, private_key) -> Any | None:
    try:
        wrapper = json.loads(payload_json)
        enc_aes_key = b64d(wrapper["enc_aes_key"])
        aes_key = private_key.decrypt(
            enc_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        nonce = b64d(wrapper["nonce"])
        tag = b64d(wrapper["tag"])
        ciphertext = b64d(wrapper["ciphertext"])
        cipher = Cipher(algorithms.AES(aes_key), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return json.loads(plaintext.decode('utf-8'))

    except Exception as e:
        print(f"Hybrid decryption error: {e}")
        return None