import os
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes # Não usado diretamente para GCM, mas útil para funções de chave

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

