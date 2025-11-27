import socket
import threading
import sys
import time
from pathlib import Path

from config.config import parse_config
from client.client_state import Client
from client.ca_handler.ca_connection import connect_and_register_to_ca
from crypto.keys.keys_handler import prepare_key_pair_generation

# Lista global de conexões
RELAY_CONNECTIONS = []
RELAY_LOCK = threading.Lock()
STOP_EVENT = threading.Event()


def handle_client(conn, addr):
    print(f"[Relay] Peer conectado: {addr}")

    with RELAY_LOCK:
        RELAY_CONNECTIONS.append(conn)

    while not STOP_EVENT.is_set():
        try:
            conn.settimeout(1.0)  # Timeout para verificar stop event
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue  # Loop para verificar STOP_EVENT

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
            # Ignorar erros normais de fecho se estivermos a sair
            if not STOP_EVENT.is_set():
                print(f"[Relay] Erro na conexão {addr}: {e}")
            break

    print(f"[Relay] Peer desconectado: {addr}")
    with RELAY_LOCK:
        if conn in RELAY_CONNECTIONS:
            RELAY_CONNECTIONS.remove(conn)
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
                continue  # Verifica o STOP_EVENT novamente
            except Exception as e:
                print(f"[Relay] Erro no accept: {e}")
    except KeyboardInterrupt:
        print("\n[Relay] A encerrar servidor...")
    finally:
        STOP_EVENT.set()
        server.close()

        # Fechar todas as conexões ativas
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

    # 1. Carregar Configuração
    try:
        host, port = parse_config(config_name)
    except Exception as e:
        print(f"[Relay] Erro ao ler config: {e}")
        sys.exit(1)

    # 2. Preparar Chaves
    if not user_path.exists():
        user_path.mkdir(parents=True, exist_ok=True)

    private_key, public_key = prepare_key_pair_generation(user_path)

    # 3. Registar na CA
    relay_client = Client(user_path, public_key, private_key)
    print("[Relay] A registar na CA...")
    try:
        connect_and_register_to_ca(relay_client)
        print("[Relay] Certificado obtido. Relay legítimo.")
    except Exception as e:
        print(f"[Relay] Falha ao registar na CA: {e}")
        sys.exit(1)

    # 4. Iniciar Servidor
    start_relay_server(host, port)


if __name__ == "__main__":
    main()