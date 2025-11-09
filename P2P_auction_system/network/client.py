import socket
import threading
import sys
import json
import queue

TEST = 1

UDP_PORT = None

if TEST == 1:
    broadcast_ip = "127.255.255.255"
else:
    broadcast_ip = "255.255.255.255"
    UDP_PORT = 5000

discovered_peers = queue.Queue()

# ========= UDP FUNCTIONS =========
def broadcast_message(s: socket.socket, message: str):
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    port = s.getsockname()[1]

    if TEST == 1:
        # Local test mode: simulate broadcast by looping through known ports
        for test_port in range(5000, 5010):
            s.sendto(message.encode(), ("127.0.0.1", test_port))
            print(f"[LOCAL BROADCAST] Sent to 127.0.0.1:{test_port}")
    else:
        # Real LAN broadcast
        s.sendto(message.encode(), (broadcast_ip, UDP_PORT))
        print(f"[LAN BROADCAST] Sent to {broadcast_ip}:{UDP_PORT}")

    print("Finished broadcast!")


def listen_for_messages(s: socket.socket, host: str, port: int):
    print(f"[LISTENING] UDP messages on port {s.getsockname()[1]}")

    while True:
        data, addr = s.recvfrom(1024)
        message = data.decode()
        print(f"[UDP] From {addr}: {message}")

        try:
            msg = json.loads(message)
            if msg.get("type") == "peer_discovery":
                    
                if addr[0] == host and addr[1] == port:
                    continue  # ignore our own broadcast messages

                print("     Peer verified, I will send my info!")

                response = peer_information_share(host, port)

                s.sendto(response.encode(), addr)
                print(f"     Sent info back to {addr[0]}:{addr[1]}")

            if msg.get("type") == "peer_info":
                peer_host = msg["host"]
                peer_port = msg["port"]
                if peer_host == host and peer_port == port:
                    continue
                
                print(f"     Peer {peer_host}:{peer_port} answered back, let's establish connection!")
                discovered_peers.put((peer_host, peer_port))

                
        except json.JSONDecodeError:
            #not json just ignore
            pass



# ========= ========= =========


# ========= TCP FUNCTIONS =========

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
        print("Current Connections:")
        print(connections)
        print("-------------")

# ========= ========= =========

def peer_information_share(host, port):
    msg = {
        "type": "peer_info",
        "host": host,
        "port": port,
        "peer_prof": "Yes"
    }

    return json.dumps(msg)

def peer_discovery_broadcast(udp_socket):
    msg = {
        "type": "peer_discovery",
        "peer_prof": "Yes"
    }

    json_msg = json.dumps(msg)

    broadcast_message(udp_socket, json_msg)


def user_auction_input(connections, stop_event):

    while not stop_event.is_set():
        msg = input()
        if msg.lower() in ("quit", "exit"):
            print("[*] Exiting on user request.")
            stop_event.set()
            break
        for conn in connections[:]:
            try:
                conn.sendall(msg.encode())
            except:
                connections.remove(conn)


def run_peer(host, port):
    global UDP_PORT

    # Shared event to signal shutdown
    stop_event = threading.Event()

    # --- TCP listener setup ---
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen()

    print(f"[*] Listening on {host}:{port}")

    # --- UDP discovery setup ---
    if UDP_PORT is None:
        UDP_PORT = port

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind((host, UDP_PORT))

    # Start UDP listener thread
    threading.Thread(
        target=listen_for_messages,
        args=(udp_socket, host, port),
        daemon=True
    ).start()

    print("   Will Broadcast!")
    peer_discovery_broadcast(udp_socket)

    # --- Connection management ---
    connections = []

    # Accept incoming peers
    threading.Thread(
        target=accept_incoming,
        args=(listener, connections),
        daemon=True
    ).start()

    # Start user input thread
    threading.Thread(
        target=user_auction_input,
        args=(connections, stop_event),
        daemon=True
    ).start()

    # --- Main loop: handle discovered peers dynamically ---
    while not stop_event.is_set():
        try:
            peer_host, peer_port = discovered_peers.get(timeout=1)
            # Check if not already connected
            connected_addrs = []
            for c in connections:
                try:
                    connected_addrs.append(c.getpeername())
                except:
                    pass

            if (peer_host, peer_port) not in connected_addrs:
                print(f"[*] Connecting to discovered peer {peer_host}:{peer_port}")
                try:
                    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    conn.connect((peer_host, peer_port))
                    connections.append(conn)
                    threading.Thread(
                        target=handle_connection,
                        args=(conn, (peer_host, peer_port)),
                        daemon=True
                    ).start()
                except Exception as e:
                    print(f"[!] Failed to connect to {peer_host}:{peer_port} -> {e}")
        except queue.Empty:
            continue

    # --- Cleanup ---
    print("[*] Shutting down peer.")
    try:
        listener.close()
    except:
        pass
    try:
        udp_socket.close()
    except:
        pass

    for c in connections:
        try:
            c.close()
        except:
            pass


def parse_config(config_file):

    with open(config_file) as fp:
        content = json.load(fp)
    
    return content["host"], int(content["port"])


def open_connection():

    if len(sys.argv) == 2:
        # Local Testing Use Config Files
        print("Peer info fetched from config file")
        host, port = parse_config(sys.argv[1])
    else: 
        #LAN Case -> For the Future
        print("LAN Case: Not implemented!")
        sys.exit(1)

    run_peer(host, port)

def main():
    open_connection()

if __name__ == "__main__":
    main()