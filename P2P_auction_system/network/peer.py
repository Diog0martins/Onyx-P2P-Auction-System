import threading
import sys
from network.peer_state import PeerState
from network.tcp import connect_to_relay

from client.message.peer_input import peer_input, menu_user
from config.config import parse_config
from local_test import TEST


def user_auction_input(connections, stop_event, config, client):
    menu_user(config)

    while not stop_event.is_set():

        msg = peer_input(config, client)

        if msg is None:
            continue

        if isinstance(msg, str) and msg.lower() == "exit":
            print("[*] Exiting on user request.")
            stop_event.set()
            break

        # Verificar se estamos ligados ao Relay
        if not connections:
            print("[!] Sem conexão ao Relay. Mensagem não enviada.")
            continue

        # Enviar para a única conexão que temos (o Relay)
        for conn in connections[:]:
            try:
                conn.sendall(msg.encode())
            except:
                connections.remove(conn)


def peer_messaging(state: PeerState, config, client):
    # Cria a thread do menu
    t = threading.Thread(
        target=user_auction_input,
        args=(state.connections, state.stop_event, config, client),
        daemon=True
    )
    t.start()
    t.join()

def run_peer_test(host, port, config, client):
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

    # 2. Iniciar a conexão persistente ao Relay
    # Substitui o antigo udp_socket e tcp_socket
    relay_thread = threading.Thread(
        target=connect_to_relay,
        args=(state, relay_host, relay_port, config, client),
        daemon=True
    )
    relay_thread.start()

    # 3. Iniciar o Menu do Utilizador (Loop Principal)
    peer_messaging(state, config, client)

    # --- Cleanup ---
    print("[*] Shutting down peer.")
    state.stop_event.set()

    for c in state.connections:
        try:
            c.close()
        except:
            pass