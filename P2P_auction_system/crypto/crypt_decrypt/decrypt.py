from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidTag
import os
import base64
import json

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

