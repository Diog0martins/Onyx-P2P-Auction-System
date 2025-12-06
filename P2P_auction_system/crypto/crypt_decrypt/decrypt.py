from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidTag
import os
import base64
import json
from cryptography.hazmat.primitives import hashes # Não usado diretamente para GCM, mas útil para funções de chave
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def decrypt_message_symmetric_gcm(payload_json: str, key: bytes) -> str:
    """
    payload_json: string JSON con "nonce", "ciphertext", y "tag"
    key: bytes de 32 bytes (AES-256)
    """
    data = json.loads(payload_json)

    # 1. Decodificar Nonce, Ciphertext e Tag
    nonce = base64.b64decode(data["nonce"])
    ciphertext = base64.b64decode(data["ciphertext"])
    tag = base64.b64decode(data["tag"]) # A Tag é crucial para a autenticação

    # 2. Configurar a cifra com AES-256 e modo GCM
    # NOTA: No GCM, é mais comum (e idiomático) usar a interface AESGCM, 
    # mas para manter a consistência com o seu uso de Cipher/modes, 
    # continuaremos com ela, embora seja um pouco mais verboso.

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    decryptor = cipher.decryptor()

    # Dados Adicionais Autenticados (AAD). Deve ser o mesmo usado na encriptação.
    aad = b""
    decryptor.authenticate_additional_data(aad)

    # 3. Desencriptar e verificar a Tag
    try:
        # A chamada finalize_with_tag faz a desencriptação E a verificação da tag
        plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize_with_tag(tag)
    except InvalidTag:
        # ESTE É O PONTO CRÍTICO: se a tag for inválida, a mensagem foi alterada.
        raise ValueError("Invalid authentication tag. Data integrity check failed.")

    # 4. Decodificar e retornar a mensagem (GCM não tem padding)
    message = plaintext_bytes.decode()
    return message

def decrypt_with_private_key(ciphertext: bytes, private_key_pem: bytes) -> bytes:
    """
    Desencripta dados usando uma chave privada RSA (PEM).
    
    ciphertext: Dados cifrados.
    private_key_pem: Chave privada do destinatário (Vendedor) em formato PEM.
    """
    # Carregar a chave privada do PEM
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None # Assumindo que a chave privada não está protegida por senha
    )

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError("A chave carregada não é uma chave privada RSA.")

    # Desencriptar usando OAEP, que deve corresponder ao esquema de padding usado na encriptação
    plaintext = private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext

