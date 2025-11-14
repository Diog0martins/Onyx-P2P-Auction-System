from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


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