import threading
from network.peer_state import PeerState
from network.udp import peer_udp_handling
from network.tcp import peer_tcp_handling, await_new_peers_conn

from client.input.peer_input import peer_input, menu_user

from network.local_test import TEST

def user_auction_input(connections, stop_event): 

    menu_user()

    while not stop_event.is_set():
        
        msg = peer_input()
        
        if msg.lower() in ("exit"):
            print("[*] Exiting on user request.")
            stop_event.set()
            break
        
        for conn in connections[:]:
            try:
                conn.sendall(msg.encode())
            except:
                connections.remove(conn)


def peer_messaging(state: PeerState):
    threading.Thread(
        target=user_auction_input,
        args=(state.connections, state.stop_event),
        daemon=True
    ).start()

def run_peer(host, port):
    if TEST == 1:
        state = PeerState(host, port)
    else: 
        state = PeerState(host, port, 5000)

    # Create sockets for peer discovery(UDP) and communication(TCP)
    udp_socket = peer_udp_handling(state)
    tcp_socket = peer_tcp_handling(state)
    
    # Main Loops to send messages and receive connections
    peer_messaging(state)
    await_new_peers_conn(state)

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