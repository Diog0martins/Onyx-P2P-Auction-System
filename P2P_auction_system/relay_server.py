import socket
import sys
import threading
from pathlib import Path

from client.ca_handler.ca_connection import connect_and_register_to_ca
from client.ca_handler.ca_message import leave_network
from client.client_state import Client
from config.config import parse_config
from crypto.keys.keys_handler import prepare_key_pair_generation
from local_test import TEST
from network.ip import get_ip

RELAY_CONNECTIONS = {} 
RELAY_LOCK = threading.Lock()
STOP_EVENT = threading.Event()
RELAY_GROUP_KEY = None

def peer_left(uuid):
    """
        Helper function that prepares a formatted message to notify the network
        that a specific peer (UUID) has disconnected.
    """

    message = leave_network(uuid)
    return (message+'\n').encode()


def handle_client(conn, addr):
    """
        Manages a single client connection on the Relay Server.
        1. Registers the client's UUID.
        2. Receives encrypted messages.
        3. Broadcasts the received message to ALL other connected clients (Echo/Relay pattern).
        4. Handles cleanup and notification when a client disconnects.
    """

    print(f"[Relay] Peer conected: {addr}")
    
    user_uuid = "NA"
    try:
        initial_data = conn.recv(1024).decode('utf-8').strip()
        if not initial_data:
            return 
        user_uuid = initial_data
        print(f"[Relay] UUID registered for {addr}: {user_uuid}")
    except Exception as e:
        print(f"[Relay] Error receiving UUID from {addr}: {e}")
        conn.close()
        return

    with RELAY_LOCK:
        RELAY_CONNECTIONS[conn] = user_uuid

    while not STOP_EVENT.is_set():
        try:
            conn.settimeout(1.0)
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue

            if not data:
                break

            # Broadcast
            msg = data
            with RELAY_LOCK:
                for c in RELAY_CONNECTIONS:
                    if c != conn:
                        try:
                            c.sendall(msg)
                        except:
                            pass

        except ConnectionResetError:
            break
        except Exception as e:
            if not STOP_EVENT.is_set():
                print(f"[Relay] Connection error {user_uuid} ({addr}): {e}")
            break

    print(f"[Relay] Peer disconnected: {user_uuid} ({addr})")
    
    to_send = peer_left(user_uuid)
    with RELAY_LOCK:
        if conn in RELAY_CONNECTIONS:
            RELAY_CONNECTIONS.pop(conn, None) 
            
        for c in RELAY_CONNECTIONS:
            try:
                c.sendall(to_send)
            except:
                pass
            
    try:
        conn.close()
    except:
        pass


def start_relay_server(host, port):
    """
        Starts the TCP server for the Relay.
        Listens for incoming peer connections and spawns a "handle_client" thread for each one.
    """

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((host, port))
        server.listen()
        server.settimeout(1.0)
        print(f"[Relay] Listening on {host}:{port} (Press CTRL+C to exit)...")
    except Exception as e:
        print(f"[Relay] Failure to start server: {e}")
        return

    try:
        while not STOP_EVENT.is_set():
            try:
                conn, addr = server.accept()
                t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Relay] Error in accept: {e}")
    except KeyboardInterrupt:
        print("\n[Relay] Shutting down server...")
    finally:
        STOP_EVENT.set()
        server.close()

        with RELAY_LOCK:
            for c in RELAY_CONNECTIONS:
                try:
                    c.close()
                except:
                    pass
        print("[Relay] Server successfully shut down.")


def main():
    """
        Entry point for the Relay Server.
        1. Loads configuration.
        2. Generates its own identity keys.
        3. Registers with the CA to obtain the Group Key.
        4. Starts the server loop.
    """

    global RELAY_GROUP_KEY
    config_name = "configRelay"
    config_path = Path("config") / config_name
    user_path = config_path / "user"

    if TEST == 1:
        try:
            host, port = parse_config(config_name)
        except Exception as e:
            print(f"[Relay] Error reading config: {e}")
            sys.exit(1)
    else:
        host = get_ip()
        port = 7000 



    if not user_path.exists():
        user_path.mkdir(parents=True, exist_ok=True)

    private_key, public_key = prepare_key_pair_generation(user_path)

    relay_client = Client(user_path, public_key, private_key)
    print("[Relay] To be recorded in the CA...")
    try:
        info = connect_and_register_to_ca(relay_client)
        RELAY_GROUP_KEY = info["group_key"]
        print("[Relay] Certificate and Group Key obtained.")
    except Exception as e:
        print(f"[Relay] Failed to register with CA: {e}")
        sys.exit(1)

    start_relay_server(host, port)

if __name__ == "__main__":
    main()