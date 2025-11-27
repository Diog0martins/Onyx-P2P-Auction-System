import threading
from network.peer_state import PeerState
from network.udp import peer_udp_handling
from network.tcp import peer_tcp_handling, await_new_peers_conn, send_to_peers

from client.ledger.ledger_handler import prepare_ledger_request

from client.message.peer_input import peer_input, menu_user

from local_test import TEST


def user_auction_input(connections, stop_event, client):

    print("     Sending ledger request!")
    request = prepare_ledger_request(client)

    if not request == None:
        send_to_peers(request, client.peer.connections)    

    menu_user()

    while not stop_event.is_set():
        
        msg = peer_input(client)

        if msg is None:
            continue

        if isinstance(msg, str) and msg.lower() == "exit":
            print("[*] Exiting on user request.")
            stop_event.set()
            break

        send_to_peers(msg, connections)

def peer_messaging(state: PeerState, client):
    threading.Thread(
        target=user_auction_input,
        args=(state.connections, state.stop_event, client),
        daemon=True
    ).start()

def run_peer_test(host, port, config, client):
    
    if TEST == 1:
        state = PeerState(host, port)
    else: 
        state = PeerState(host, port, 5000)

    client.peer = state

    # Create sockets for peer discovery(UDP) and communication (TCP)
    udp_socket = peer_udp_handling(state)
    tcp_socket = peer_tcp_handling(client)
    
    # Main Loops to send messages and receive connections
    peer_messaging(state, client)
    await_new_peers_conn(state, config, client)

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