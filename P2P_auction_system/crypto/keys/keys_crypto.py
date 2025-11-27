from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def load_rsa_public_key(pub_bytes: str) -> rsa.RSAPublicKey:
    
    try:
        key = serialization.load_pem_public_key(pub_bytes)
        if not isinstance(key, rsa.RSAPublicKey):
            raise ValueError("Not an RSA public key")
        return key
    except Exception as e:
        raise ValueError(f"Invalid RSA public key: {e}")


def get_pub_bytes(rsa_public_key): 

    ca_pub_bytes = rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return ca_pub_bytes


def load_private_and_public_key(private_key_path, public_key_path):

    # Load private key
    with open(private_key_path, "rb") as f:
        private_data = f.read()
        private_key = serialization.load_pem_private_key(private_data, password=None)

    # Load public key
    with open(public_key_path, "rb") as f:
        public_data = f.read()
        public_key = serialization.load_pem_public_key(public_data)

    return private_key, public_key


def generate_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Convert private key to PEM
    private_pem = private_key.private_bytes(
        encoding = serialization.Encoding.PEM,
        format = serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm = serialization.NoEncryption()
    )

    # Convert public key to PEM
    public_pem = private_key.public_key().public_bytes(
        encoding = serialization.Encoding.PEM,
        format = serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem

import os

def generate_aes_key() -> bytes:
    return os.urandom(32)
