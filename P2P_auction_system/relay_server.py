import socket
import threading
import sys
import time
from pathlib import Path

from config.config import parse_config
from client.client_state import Client
from client.ca_handler.ca_connection import connect_and_register_to_ca
from client.ca_handler.ca_message import leave_network
from crypto.keys.keys_handler import prepare_key_pair_generation

RELAY_CONNECTIONS = {} 
RELAY_LOCK = threading.Lock()
STOP_EVENT = threading.Event()


def peer_left(uuid):
    message = leave_network(uuid)
    #print(message)
    return (message+'\n').encode()


def handle_client(conn, addr):
    print(f"[Relay] Peer conectado: {addr}")
    
    user_uuid = "NA"
    try:
        # Assume-se que a primeira mensagem do cliente é o seu UUID
        # Ajuste o tamanho 1024 se necessário
        initial_data = conn.recv(1024).decode('utf-8').strip()
        if not initial_data:
            return # Se não enviou nada, desconecta logo
        user_uuid = initial_data
        print(f"[Relay] UUID registado para {addr}: {user_uuid}")
    except Exception as e:
        print(f"[Relay] Erro ao receber UUID de {addr}: {e}")
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
                print(f"[Relay] Erro na conexão {user_uuid} ({addr}): {e}")
            break

    print(f"[Relay] Peer desconectado: {user_uuid} ({addr})")
    
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
        print(f"[Relay] À escuta em {host}:{port} (Pressiona CTRL+C para sair)...")
    except Exception as e:
        print(f"[Relay] Falha ao iniciar servidor: {e}")
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
                print(f"[Relay] Erro no accept: {e}")
    except KeyboardInterrupt:
        print("\n[Relay] A encerrar servidor...")
    finally:
        STOP_EVENT.set()
        server.close()

        with RELAY_LOCK:
            for c in RELAY_CONNECTIONS:
                try:
                    c.close()
                except:
                    pass
        print("[Relay] Servidor encerrado com sucesso.")


def main():
    config_name = "configRelay"
    config_path = Path("config") / config_name
    user_path = config_path / "user"

    try:
        host, port = parse_config(config_name)
    except Exception as e:
        print(f"[Relay] Erro ao ler config: {e}")
        sys.exit(1)

    if not user_path.exists():
        user_path.mkdir(parents=True, exist_ok=True)

    private_key, public_key = prepare_key_pair_generation(user_path)

    relay_client = Client(user_path, public_key, private_key)
    print("[Relay] A registar na CA...")
    try:
        connect_and_register_to_ca(relay_client)
        print("[Relay] Certificado obtido. Relay legítimo.")
    except Exception as e:
        print(f"[Relay] Falha ao registar na CA: {e}")
        sys.exit(1)

    start_relay_server(host, port)


if __name__ == "__main__":
    main()