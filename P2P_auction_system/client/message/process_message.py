import json
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm, encrypt_with_public_key
from client.ledger.ledger_handler import load_public_ledger, ledger_request_handler, ledger_update_handler
from crypto.keys.group_keys import find_my_new_key
from client.message.auction.auction_handler import update_auction_higher_bid, add_auction
from datetime import datetime
import time
import base64

def is_auction_closed(auctions, auction_id):
    now = int(time.time())
    
    auction_data = auctions["auction_list"].get(auction_id)
    
    if not auction_data:
        return True

    closing_time = auction_data.get("closing_date")

    if closing_time is None:
        return False
        
    return now >= closing_time

def verify_double_spending2(token_id, config):
    ledger = load_public_ledger(config)
    for entry in ledger:
        # Verifica se a entrada tem token e se o ID é igual
        if "token" in entry:
            existing_id = entry["token"].get("token_id")
            if existing_id == token_id:
                return True # Já foi gasto!
    return False

def verify_double_spending(token_id, client):
    return client.ledger.token_used(token_id)

def update_personal_auctions(client, msg):
    if msg.get("type") == "auction":
        auction_id = msg.get("id")
        min_bid = msg.get("min_bid")
        closing_date = msg.get("closing_date")
        add_auction(client.auctions, auction_id, min_bid, closing_date, "False")

    else:
        auction_id = msg.get("auction_id")
        new_bid = msg.get("bid")

        update_auction_higher_bid(client.auctions, auction_id, new_bid, "False")


def process_message(msg, client_state):
    try:
        obj = json.loads(msg)
    except:
        print("[!] Received non-JSON message; ignored")
        print("RAW MESSAGE:", repr(msg))
        return


    mtype = obj.get("type")
    print(obj)
    if mtype in ("auction", "bid", "ledger_request", "ledger_update", "auctionEnd"):
        
        token_data = obj.get("token")
        if not token_data:
            print(f"[!] Mensagem {mtype} rejeitada: Sem token.")
            return

        token_id = token_data.get("token_id")
        token_sig = token_data.get("token_sig")

        if not client_state.token_manager.verify_token(token_id, token_sig):
            print(f"[Security] ALERTA: Assinatura do Token inválida na mensagem {obj.get('id')}. Ignorada.")
            return

        if verify_double_spending(token_id, client_state):
            print(f"[Security] ALERTA: Tentativa de Double Spending (Token {token_id}). Ignorada.")
            return

        if mtype in ("auction", "bid"):

            should_process = True
    
            if mtype == "bid":
                if is_auction_closed(client_state.auctions, obj.get('auction_id')):
                    print(f"[X] Oferta rejeitada. Tempo expirado ({int(time.time())})")
                    should_process = False

            if should_process:
                if client_state.ledger.add_action(obj) == 1:
                    client_state.ledger.save_to_file(client_state.user_path / "ledger.json") 
                update_personal_auctions(client_state, obj)
                print(f"[✓] Stored {mtype} (id={obj.get('id')}) in ledger")

        elif mtype == "auctionEnd":
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

            #Sou o ganhador?
            if info.get("my_bid") == 'True':

                print("Ganhei !!!")
                #Crio a msg
                my_winning_token = info.get("token")

                if my_winning_token:
                    # my_winning_token es un diccionario, procede a extraer el ID
                    token_id = my_winning_token.get("token_id")
                    print("BOA CRLHOOOOOOOOOOOO")
                    
                    # ... tu lógica de procesamiento posterior aquí ...
                    
                else:
                    # La clave "token" no estaba en la información de la subasta (info)
                    print(auction_list)
                    print("[ERROR] Subasta finalizada sin token de ganador en los datos.")
                    print("[ERROR] Subasta finalizada sin token de ganador en los datos.")
                    print("[ERROR] Subasta finalizada sin token de ganador en los datos.")
                    print("[ERROR] Subasta finalizada sin token de ganador en los datos.")
                    print("[ERROR] Subasta finalizada sin token de ganador en los datos.")
                    print("[ERROR] Subasta finalizada sin token de ganador en los datos.")
                    # Puedes manejar el caso donde no hay token si es un escenario válido
                # token_id = my_winning_token.get("token_id")
                
                # if token_id: 
                    
                #     r_value = client_state.token_manager.get_blinding_factor_r(token_id)

                #     if r_value is None:
                #         print(f"[!] Erro Crítico: Token ID {token_id} não encontrado na carteira local.")
                #         return

                #     seller_public_key_pem = obj.get("public_key")
                #     if seller_public_key_pem is None:
                #         print("[!] Erro: Chave pública do vendedor não encontrada na informação da subasta.")
                #         return

                #     # r
                #     # el otro parametro
                #     # mi llave publica
                #     # token ??
                #     # id auction
                #     # calculo el A

                #     # 1. CONSTRUIR PAYLOAD PRIVADO (Mensagem Interna)
                #     private_payload_dict = {
                #         "token_id": token_id,
                #         "blinding_factor_r": str(r_value),
                #         "public_key": client_state.public_key
                #     }
                #     private_payload_json = json.dumps(private_payload_dict)
                #     private_data_bytes = private_payload_json.encode('utf-8')

                #     # 2. ENCRIPTAR ASSIMETRICAMENTE (RSA com chave pública do VENDEDOR)
                #     # O payload resultante é uma sequência de BYTES cifrados
                #     encrypted_private_bytes = encrypt_with_public_key(private_data_bytes, seller_public_key_pem.encode('utf-8'))

                #     # 3. CONSTRUIR PAYLOAD DE TRANSPORTE (Mensagem Externa)
                #     # Codificamos os bytes cifrados para Base64 para que possam ser colocados no JSON
                #     base64_private_payload = base64.b64encode(encrypted_private_bytes).decode('ascii')

                #     response_msg_payload = {
                #         "type": "winner_reveal", 
                #         "auction_id": auction_target,
                #         "private_info": base64_private_payload
                #     }

                #     # 4. ENCRIPTAR SIMETRICAMENTE (AES-GCM com Group Key)
                #     response_json = json.dumps(response_msg_payload)
                #     c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

                #     print(f"[WINNER] Enviando revelação do factor cegador 'r' para a subasta {auction_target}...")
                #     # send_to_peers(c_response_json, client_state.peer.connections)
                    
                #     # Opcional: Eliminar la subasta de la lista local
                #     # del client_state.auctions["auction_list"][auction_target]
                    
                # else:
                #     return
            else:
                return

        elif mtype == "ledger_request":
            from network.tcp import send_to_peers
            update_json = ledger_request_handler(obj.get("request_id"), client_state)

            if update_json:
                c_update_json = encrypt_message_symmetric_gcm(update_json, client_state.group_key)
                send_to_peers(c_update_json, client_state.peer.connections)
        
        elif mtype == "ledger_update":
            if not client_state.ledger_request_id == 0:
                print("Receive updated ledger!")
                ledger_update_handler(client_state, obj)
    
    elif mtype == "new_key":
       keys = obj.get("encrypted_keys")
       print(client_state.private_key)
       new_group_key = find_my_new_key(keys, client_state.private_key)

       if not new_group_key == None:
           client_state.group_key = new_group_key

    else:
        print(f"[?] Unknown message type received: {mtype}")