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
    # 1. Gerar Nonce aleatório (AES-GCM usa 12 bytes por padrão)
    # O nonce DEVE ser único para cada encriptação com a mesma chave.
    nonce = os.urandom(12)

    # 2. Configurar a cifra com AES-256 e modo GCM
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()

    # Dados Adicionais Autenticados (AAD). Opcional, mas boa prática.
    # Neste caso, usamos AAD vazio, mas é autenticado junto com a mensagem.
    aad = b""
    encryptor.authenticate_additional_data(aad)

    # 3. Encriptar a mensagem (sem padding)
    ciphertext = encryptor.update(message.encode()) + encryptor.finalize()

    # 4. Obter a tag de autenticação GCM
    tag = encryptor.tag

    # 5. Criar JSON com Nonce + ciphertext + tag
    payload = {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "tag": base64.b64encode(tag).decode()
    }
    return json.dumps(payload)

def encrypt_with_public_key(message_bytes: bytes, public_key_pem: bytes) -> bytes:
    """
    Encripta dados usando uma chave pública RSA (PEM).
    
    message_bytes: Dados a serem cifrados (devem ser curtos para RSA).
    public_key_pem: Chave pública do destinatário (Vendedor) em formato PEM.
    """
    # Carregar a chave pública do PEM
    public_key = serialization.load_pem_public_key(public_key_pem)

    if not isinstance(public_key, rsa.RSAPublicKey):
        raise TypeError("A chave carregada não é uma chave pública RSA.")

    # Encriptar usando OAEP (Optimal Asymmetric Encryption Padding)
    ciphertext = public_key.encrypt(
        message_bytes,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

