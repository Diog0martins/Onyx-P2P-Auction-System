import threading, socket, queue, time
import traceback
from network.peer_state import PeerState
from client.message.process_message import process_message
from crypto.crypt_decrypt.decrypt import decrypt_message_symmetric


# ======== TCP Utilities ========

def send_to_peers(msg, connections):
    # Enviar a todos los peers
    for conn in connections[:]:
        try:
            conn.sendall((msg +"\n").encode())
        except:
            connections.remove(conn)


# Function to handle messages from peers
def handle_connection(conn, addr, client_state):
    print(f"[+] Connected: {addr}")
    buffer = ""
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                c_msg, buffer = buffer.split("\n", 1)
                msg = decrypt_message_symmetric(c_msg, client_state.group_key)
                process_message(msg, client_state)
        
        except ConnectionResetError:
            print(f"[-] Ligação fechada abruptamente por {addr}")
            break

        except OSError as e:
            if client_state.peer.stop_event.is_set():
                break
            print(f"[-] Erro de socket (provável desconexão): {e}")
            break

        except Exception as e:
            print(f"[!] ERRO CRÍTICO ao processar mensagem de {addr}: {e}")
            traceback.print_exc()
            break

    if not client_state.peer.stop_event.is_set():
        print(f"[-] Disconnected: {addr}")
    try:
        conn.close()
    except:
        pass


# Functions to accpet and establish connections with new peers
def accept_incoming(listener, connections, client_state):
    while True:
        try:
            conn, addr = listener.accept()
            connections.append(conn)
            threading.Thread(
                target=handle_connection,
                args=(conn, addr, client_state),
                daemon=True
            ).start()
        except Exception as e:
            print(f"[!] Error in accept_incoming: {e}")


def await_new_peers_conn(state: PeerState, client_state):
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
                            args=(conn, (peer_host, peer_port), client_state),
                            daemon=True
                        ).start()
                    except Exception as e:
                        print(f"[!] Failed to connect to {peer_host}:{peer_port} -> {e}")
            except queue.Empty:
                continue

# ======== ======== ========


# ======== TCP Handler ========

def peer_tcp_handling(client_state):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((client_state.peer.host, client_state.peer.port))
    listener.listen()  

    print(f"[*] Listening on {client_state.peer.host}:{client_state.peer.port}")

    threading.Thread(
        target=accept_incoming,
        args=(listener, client_state.peer.connections, client_state),
        daemon=True
    ).start()

    return listener

# ======== ======== ========

def connect_to_relay(state: PeerState, relay_host, relay_port, client_state):
    print(f"[*] A conectar ao RELAY em {relay_host}:{relay_port}...")
    while not state.stop_event.is_set():
        try:
            if len(state.connections) > 0:
                state.stop_event.wait(5)
                continue

            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((relay_host, relay_port))

            print(f"[+] Conectado ao Relay com sucesso!")
            state.connections.append(conn)

            handle_connection(conn, (relay_host, relay_port), client_state)

            print("[!] Conexão ao Relay perdida. A tentar reconectar...")
            if conn in state.connections:
                state.connections.remove(conn)

        except ConnectionRefusedError:
            print("[!] Relay indisponível. A tentar novamente em 3s...")
            state.stop_event.wait(3)
        except Exception as e:
            print(f"[!] Erro na ligação ao Relay: {e}")
            state.stop_event.wait(3)