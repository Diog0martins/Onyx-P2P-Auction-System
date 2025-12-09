import threading, socket
from design.ui import UI
from network.peer_state import PeerState
from client.message.process_message import process_message
from crypto.crypt_decrypt.decrypt import decrypt_message_symmetric_gcm


# ======== TCP Utilities ========

def send_to_peers(msg, connections):
    """
        Broadcasts a message to a list of active TCP connections.
        Appends a newline character as a delimiter to ensure proper message framing.
        Handles disconnected sockets by removing them from the list.
    """

    for conn in connections[:]:
        try:
            conn.sendall((msg + "\n").encode('utf-8'))
        except Exception:
            if conn in connections:
                connections.remove(conn)
            try:
                conn.close()
            except:
                pass

def handle_connection(conn, addr, client_state):
    """
        The main TCP listener loop for a specific connection.
        1. Reads raw bytes from the socket into a buffer.
        2. Handles TCP fragmentation by processing data only when a newline delimiter is found.
        3. Decrypts incoming messages using the Group Key (AES-GCM).
        4. Passes the valid message to the application logic (process_message).
    """

    UI.success(f"Connected: {addr}")

    buffer = b""

    while True:
        try:
            conn.settimeout(1.0)
            try:
                data = conn.recv(8192)
            except socket.timeout:
                if client_state.peer.stop_event.is_set():
                    break
                continue
            except OSError:
                break

            if not data:
                break

            buffer += data

            while b"\n" in buffer:
                c_msg_bytes, buffer = buffer.split(b"\n", 1)

                try:
                    c_msg = c_msg_bytes.decode('utf-8').strip()
                except UnicodeDecodeError:
                    UI.warn(f"Decoding error ignored in connection {addr}")
                    continue

                if not c_msg:
                    continue

                try:
                    try:
                        msg = decrypt_message_symmetric_gcm(c_msg, client_state.group_key)
                        process_message(msg, client_state)
                    except Exception:
                        process_message(c_msg, client_state)

                except Exception as e:
                    UI.error(f"Error processing message: {e}")

        except ConnectionResetError:
            UI.warn(f"Connection closed by {addr}")
            break

        except Exception as e:
            if not client_state.peer.stop_event.is_set():
                UI.error(f"Critical error in connection {addr}: {e}")
            break

    if not client_state.peer.stop_event.is_set():
        UI.sys(f"Disconnected: {addr}")
    try:
        conn.close()
    except:
        pass

def accept_incoming(listener, connections, client_state):
    """
        Background thread loop that accepts new incoming TCP connections
        and spawns a handler thread for each one.
    """

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
            UI.error(f"Error in accept_incoming: {e}")


def await_new_peers_conn(state: PeerState, client_state):
    """Legacy function reserved for future P2P direct connection logic (currently unused)."""
    pass

# ======== TCP Handler ========

def peer_tcp_handling(client_state):
    """
        Sets up the local TCP server socket to listen for incoming connections.
        Starts the "accept_incoming" thread.
    """

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((client_state.peer.host, client_state.peer.port))
    listener.listen()

    UI.sys(f"Listening on {client_state.peer.host}:{client_state.peer.port}")

    threading.Thread(
        target=accept_incoming,
        args=(listener, client_state.peer.connections, client_state),
        daemon=True
    ).start()

    return listener


def connect_to_relay(state: PeerState, relay_host, relay_port, client_state):
    """
        Maintains a persistent outbound connection to the Relay Server.
        Includes logic for automatic reconnection (retry mechanism) if the connection is lost.
        Sends the client's UUID upon successful connection for identification.
    """

    UI.sys(f"Connecting to RELAY at {relay_host}:{relay_port}...")

    while not state.stop_event.is_set():
        conn = None
        try:
            if len(state.connections) > 0:
                state.stop_event.wait(5)
                continue

            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((relay_host, relay_port))

            UI.success(f"Successfully connected to Relay!")

            state.connections.append(conn)

            conn.sendall((client_state.uuid + "\n").encode('utf-8'))

            handle_connection(conn, (relay_host, relay_port), client_state)

            UI.warn("Connection to Relay lost. Attempting to reconnect...")

        except ConnectionRefusedError:
            UI.warn("Relay unavailable. Retrying in 3 seconds....")
            state.stop_event.wait(3)

        except Exception as e:
            UI.error(f"Error connecting to Relay: {e}")
            state.stop_event.wait(3)

        finally:
            if conn:
                if conn in state.connections:
                    state.connections.remove(conn)
                try:
                    conn.close()
                except:
                    pass