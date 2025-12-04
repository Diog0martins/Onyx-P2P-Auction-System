from cryptography.hazmat.primitives import serialization
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm, encrypt_with_public_key
from crypto.crypt_decrypt.decrypt import decrypt_with_private_key, decrypt_message_symmetric_gcm
from datetime import datetime
import json
import time
from crypto.encoding.b64 import b64e, b64d
from crypto.keys.keys_crypto import generate_aes_key

def handle_winner_reveal(client_state, obj):
    """
    Lógica del VENDEDOR para procesar el mensaje 'winner_reveal' y obtener el factor 'r'.
    """
    auction_id = obj.get("auction_id")
    
    # 1. RECUPERAR CLAVES LOCALES (Vendedor)
    my_auction = client_state.auctions["my_auctions"].get(auction_id)
    
    if my_auction is None:
        print(f"[ERROR] Recibido WINNER_REVEAL para subasta {auction_id} que no me pertenece.")
        return

    # La clave privada de la subasta está almacenada como STRING PEM.
    my_auction_private_key_pem = my_auction.get("private_key")
    
    if my_auction_private_key_pem is None:
        # ... (erro)
        return

    cleaned_pem_string = my_auction_private_key_pem.strip()
    private_key_pem_bytes = cleaned_pem_string.encode('utf-8') 
    
    # 2. Desencriptar a Deal Key (Capa Intermédia - RSA Asimétrica)
    deal_key_encrypted_b64 = obj.get("deal_key")

    # NOTA: O payload cifrado 'deal_key_encrypted_b64' DEVE ser decodificado:
    try:
        deal_key_encrypted_bytes = b64d(deal_key_encrypted_b64) # <-- b64d só aqui!
    except Exception as e:
        print(f"[ERROR] Falha ao decodificar Base64 da Deal Key cifrada: {e}")
        return
    
    try:
        # load_pem_private_key AGORA funciona porque recebe o PEM (bytes)
        deal_key_bytes = decrypt_with_private_key(
            deal_key_encrypted_bytes, 
            private_key_pem_bytes
        )
        # ... (Restante da lógica)
    except Exception as e:
        print(f"[SECURITY] Falha na Desencriptação RSA (Deal Key): {e}")
        return

    # 3. DESENCRIPTAR CONTENIDO PRIVADO (Capa Interna - Deal Key Simétrica)
    
    # El 'private_info' es una string JSON con {nonce, ciphertext, tag} (GCM)
    private_payload_crypted_json = obj.get("private_info")
    
    # Decifrar el payload interno usando la deal_key (bytes)
    try:
        private_payload_json = decrypt_message_symmetric_gcm(
            private_payload_crypted_json, 
            deal_key_bytes # La Deal Key ya está en bytes
        )
        
        # Cargar el JSON interno
        private_info_obj = json.loads(private_payload_json)

        # 4. RESULTADO FINAL
        token_id_revelado = private_info_obj.get("token_winner_bid_id")
        r_revelado = private_info_obj.get("blinding_factor_r")
        
        print("\n=== REVELACIÓN DEL GANADOR PROCESADA ===")
        print(f"Token ID del Ganador: {token_id_revelado}")
        print(f"Factor Cegador 'r': {r_revelado}")
        
        # TODO: Aquí va la verificación final del r para confirmar el ganador.
        
    except Exception as e:
        print(f"[SECURITY] Falha na Desencriptação GCM (Conteúdo Privado): {e}")
        return