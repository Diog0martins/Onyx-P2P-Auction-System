import socket
import threading
import sys
import json
import time
from pathlib import Path

from config.config import parse_config
from client.client_state import Client
from client.ca_handler.ca_connection import connect_and_register_to_ca
from client.ca_handler.ca_message import leave_network
from crypto.keys.keys_handler import prepare_key_pair_generation
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm

RELAY_CONNECTIONS = {} 
RELAY_LOCK = threading.Lock()
STOP_EVENT = threading.Event()
RELAY_GROUP_KEY = None

def peer_left(uuid):
    message = leave_network(uuid)
    return (message+'\n').encode()


def handle_client(conn, addr):
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
    global RELAY_GROUP_KEY
    config_name = "configRelay"
    config_path = Path("config") / config_name
    user_path = config_path / "user"

    try:
        host, port = parse_config(config_name)
    except Exception as e:
        print(f"[Relay] Error reading config: {e}")
        sys.exit(1)

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