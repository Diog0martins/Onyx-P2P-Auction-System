import threading, socket, queue
from network.peer_state import PeerState

# ======== TCP Utilities ========

# Function to handle messages from peers
def handle_connection(conn, addr):
    print(f"[+] Connected: {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            print(f"[{addr}] {data.decode()}")
        except:
            break
    print(f"[-] Disconnected: {addr}")
    conn.close()


# Functions to accpet and establish connections with new peers
def accept_incoming(listener, connections):
    while True:
        conn, addr = listener.accept()
        connections.append(conn)
        threading.Thread(target=handle_connection, args=(conn, addr), daemon=True).start()


def await_new_peers_conn(state: PeerState):
    while not state.stop_event.is_set():
            try:
                peer_host, peer_port = state.discovered_peers.get(timeout=1)
                # Check if not already connected
                connected_addrs = []
                for c in state.connections:
                    try:
                        connected_addrs.append(c.getpeername())
                    except:
                        pass

                if (peer_host, peer_port) not in connected_addrs:
                    print(f"[*] Connecting to discovered peer {peer_host}:{peer_port}")
                    try:
                        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        conn.connect((peer_host, peer_port))
                        state.connections.append(conn)
                        threading.Thread(
                            target=handle_connection,
                            args=(conn, (peer_host, peer_port)),
                            daemon=True
                        ).start()
                    except Exception as e:
                        print(f"[!] Failed to connect to {peer_host}:{peer_port} -> {e}")
            except queue.Empty:
                continue

# ======== ======== ========




# ======== TCP Handler ========

def peer_tcp_handling(state: PeerState): 
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((state.host, state.port))
    listener.listen()  

    print(f"[*] Listening on {state.host}:{state.port}")

    threading.Thread(
        target=accept_incoming,
        args=(listener, state.connections),
        daemon=True
    ).start()

    return listener

# ======== ======== ========