from cryptography.hazmat.primitives import serialization
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm, encrypt_with_public_key
from datetime import datetime
import json
import time
from crypto.encoding.b64 import b64e

def handle_auction_end(client_state, obj):
    from network.tcp import send_to_peers
    now = int(time.time())

    auction_list = client_state.auctions["auction_list"]
    auction_target = obj.get('auction_id')
    info = auction_list.get(auction_target)

    if info is None:
        print(f"[INFO] Recebido AUCTION_END para subasta desconhecida {auction_target}")
        return

    closing_timestamp = info.get("closing_date")
    closing_dt = datetime.fromtimestamp(closing_timestamp)
    print(f"\n--- 🔔 AVISO DE FECHE DE LEILAO ---")
    print(f"LEILAO FINALIZADO: ID {auction_target}")
    print(f"Hora de Feche Regitada: {closing_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Hora Atual: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"-----------------------------------\n")

    # If USer consideres himself the winner
    if info.get("my_bid") == 'True':
        
        # Get token used the last bid
        my_winning_token = info.get("last_bid_token_data")
        
        # Prepare proof that token is owned by user
        if my_winning_token:

            token_id = my_winning_token.get("token_id")
            
            if token_id:                     
                r_value = client_state.token_manager.get_blinding_factor_r(token_id)

                if r_value is None:
                    print(f"[!] Erro Crítico: Token ID {token_id} não encontrado na wallet local.")
                    return

                # Need Parameters
                # random number used to blind - r
                # el otro parametro
                # mi llave publica
                # token ??
                # id auction
                # calculo el A

                # Prepare public key to send to prove identity 
                rsa_public_key_object = client_state.public_key
                public_key_pem_str = rsa_public_key_object.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode('utf-8') 

                # Dedicated Encryption to auctioner

                print("==================================================================================")
                auction_public_key_pem = client_state.ledger.find_auction_public_key(auction_target)
                print(auction_public_key_pem)
                
                r_bytes = (str(r_value))
                r_bytes_group_encrypted = encrypt_message_symmetric_gcm(r_bytes, client_state.group_key)
                encrypted_blinding_r = encrypt_with_public_key(r_bytes_group_encrypted.encode(), auction_public_key_pem.encode("utf-8"))

                public_key_pem_bytes = public_key_pem_str.encode()
                encrypted_private_bytes = encrypt_with_public_key(public_key_pem_bytes, auction_public_key_pem.encode("utf-8"))


                # 1. Construct private payload to Auction Creator
                private_payload_dict = {
                    "token_winner_bid_id": token_id,
                    "blinding_factor_r": encrypted_blinding_r,
                    "public_key": encrypted_private_bytes
                }


                try:
                    token_data = client_state.token_manager.get_token()
                except Exception as e:
                    print(f"[!] Não foi possível criar Auction: {e}")
                    return None

                response_msg_payload = {
                    "type": "winner_reveal", 
                    "auction_id": auction_target,
                    "token": token_data,
                    "private_info": private_payload_dict
                }

                # 4. ENCRIPTAR SIMETRICAMENTE (AES-GCM com Group Key)
                response_json = json.dumps(response_msg_payload)
                c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

                print(f"[WINNER] Enviando revelação do factor cegador 'r' para a subasta {auction_target}...")
                send_to_peers(c_response_json, client_state.peer.connections)
                
                # Opcional: Eliminar la subasta de la lista local
                # del client_state.auctions["auction_list"][auction_target]
            
            else:
                return
            
            # ... tu lógica de procesamiento posterior aquí ...
            
        else:
            # La clave "token" no estaba en la información de la subasta (info)
            print(auction_list)
            print("[ERROR] Subasta finalizada sin token de ganador en los datos.")
            # Puedes manejar el caso donde no hay token si es un escenario válido
        token_id = my_winning_token.get("token_id")
        
        
    else:
        return