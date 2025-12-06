import threading
import sys
import json, random
from network.peer_state import PeerState
from network.tcp import connect_to_relay
from network.udp import peer_udp_handling
from network.tcp import peer_tcp_handling, await_new_peers_conn
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm
from network.tcp import peer_tcp_handling, await_new_peers_conn, send_to_peers

from client.ledger.ledger_handler import prepare_ledger_request

from client.message.peer_input import peer_input, menu_user
from config.config import parse_config
from local_test import TEST

import threading
import time
from datetime import datetime
from cryptography.hazmat.primitives import serialization

def check_auctions(client_state):

    while client_state.is_running:
        
        now = int(time.time())
        
        auctions_to_check = list(client_state.auctions["my_auctions"].keys())
        
        for auction_id in auctions_to_check:
            
            auction_data_list = client_state.auctions["auction_list"].get(auction_id)
            
            if not auction_data_list:
                continue 

            closing_timestamp = auction_data_list.get("closing_date")

            if closing_timestamp and now >= closing_timestamp and auction_data_list.get("finished") == False:
                
                closing_dt = datetime.fromtimestamp(closing_timestamp)
                print(f"\n--- 🔔 AVISO DE FECHE DE LEILAO ---")
                print(f"LEILAO FINALIZADO: ID {auction_id}")
                print(f"Hora de Feche Regitada: {closing_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Hora Atual: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"-----------------------------------\n")

                # 1. Obtenha o objeto chave (assumindo que ele está nos seus dados do leilão)
                # rsa_public_key_object = client_state.public_key

                # 2. CONVERTER PARA STRING PEM
                # public_key_pem_str = rsa_public_key_object.public_bytes(
                #     encoding=serialization.Encoding.PEM,
                #     format=serialization.PublicFormat.SubjectPublicKeyInfo
                # ).decode('utf-8') # Decodificar para string para ser JSON serializável

                try:
                    token_data = client_state.token_manager.get_token()
                except Exception as e:
                    print(f"[!] Não foi possível criar Auction: {e}")
                    return None

                # Creo msg de tipo auctionEnd
                auctionEnd_obj = {
                    "type": "auctionEnd",
                    "auction_id": auction_id,
                    "token": token_data,
                }
                # Encripto msg
                auctionEnd_json = json.dumps(auctionEnd_obj)
                msg = encrypt_message_symmetric_gcm(auctionEnd_json, client_state.group_key)
                # Envio msg
                send_to_peers(msg, client_state.peer.connections)
                client_state.auctions["auction_list"][auction_id]["finished"] = True
                
        time.sleep(10)

    print("[INFO] Hilo de monitorización de subastas finalizado.")

def user_auction_input(connections, stop_event, client):

    print("     Sending ledger request!")
    request = prepare_ledger_request(client)

    if not request == None:
        c_request = encrypt_message_symmetric_gcm(request, client.group_key)
        send_to_peers(c_request, client.peer.connections)    

    menu_user()

    while not stop_event.is_set():
        
        msg = peer_input(client)

        if msg is None:
            continue

        if isinstance(msg, str) and msg.lower() == "exit":
            print("[*] Exiting on user request.")
            stop_event.set()
            client.is_running = False
            break

        msg = encrypt_message_symmetric_gcm(msg, client.group_key)

        if not connections:
            print("[!] Sem conexão ao Relay. Mensagem não enviada.")
            continue

        # Enviar para a única conexão que temos (o Relay)
        send_to_peers(msg, client.peer.connections)

def peer_messaging(state: PeerState, client):
    t = threading.Thread(
        target=user_auction_input,
        args=(state.connections, state.stop_event, client),
        daemon=True
    )
    t.start()
    t.join()

def run_peer(host, port, client):
    # 1. Carregar configuração do Relay dinamicamente
    try:
        relay_host, relay_port = parse_config("configRelay")
        print(f"[*] Configuração do Relay carregada: {relay_host}:{relay_port}")
    except Exception as e:
        print(f"[!] Erro crítico: Não foi possível ler 'config/configRelay/configRelay.json'.")
        print(f"[!] Detalhes: {e}")
        sys.exit(1)

    if TEST == 1:
        state = PeerState(host, port)
    else:
        state = PeerState(host, port, 5000)

    client.peer = state

    # 2. Iniciar a conexão persistente ao Relay
    # Substitui o antigo udp_socket e tcp_socket
    relay_thread = threading.Thread(
        target=connect_to_relay,
        args=(state, relay_host, relay_port, client),
        daemon=True
    )

    auctions_thread = threading.Thread(
        target = check_auctions,
        args = (client,),
        daemon=True
    )

    relay_thread.start()
    auctions_thread.start()

    peer_udp_handling(client)

    # 3. Iniciar o Menu do Utilizador (Loop Principal)
    peer_messaging(state, client)
    await_new_peers_conn(state, client)

    # --- Cleanup ---
    print("[*] Shutting down peer.")
    state.stop_event.set()

    for c in state.connections:
        try:
            c.close()
        except:
            pass