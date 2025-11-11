import threading
from network.peer_state import PeerState
from network.udp import peer_udp_handling
from network.tcp import peer_tcp_handling, await_new_peers_conn

from client.input.peer_input import peer_input, menu_user

from network.local_test import TEST

def user_auction_input(connections, stop_event, config): 

    menu_user()

    while not stop_event.is_set():
        
        msg = peer_input(config)

        if msg is None:
            continue

        if isinstance(msg, str) and msg.lower() == "exit":
            print("[*] Exiting on user request.")
            stop_event.set()
            break

        # Enviar a todos los peers
        for conn in connections[:]:
            try:
                conn.sendall(msg.encode())
            except:
                connections.remove(conn)

def peer_messaging(state: PeerState, config):
    threading.Thread(
        target=user_auction_input,
        args=(state.connections, state.stop_event, config),
        daemon=True
    ).start()

def run_peer_test(host, port, config):
    if TEST == 1:
        state = PeerState(host, port)
    else: 
        state = PeerState(host, port, 5000)

    # Create sockets for peer discovery(UDP) and communication(TCP)
    udp_socket = peer_udp_handling(state)
    tcp_socket = peer_tcp_handling(state, config)
    
    # Main Loops to send messages and receive connections
    peer_messaging(state, config)
    await_new_peers_conn(state, config)

    # --- Cleanup ---
    print("[*] Shutting down peer.")
    try:
        tcp_socket.close()
    except:
        pass
    try:
        udp_socket.close()
    except:
        pass

    for c in state.connections:
        try:
            c.close()
        except:
            pass