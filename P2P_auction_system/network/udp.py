import threading, socket, json
from network.peer_state import PeerState
from network.local_test import TEST

# ======== UDP Message Layouts ========

def peer_information_share(host, port):
    msg = {
        "type": "peer_info",
        "host": host,
        "port": port,
        "peer_prof": "Yes"
    }

    return json.dumps(msg)

def peer_discovery_broadcast(udp_socket: socket.socket, state: PeerState):
    msg = {
        "type": "peer_discovery",
        "peer_prof": "Yes"
    }

    json_msg = json.dumps(msg)

    broadcast_message(udp_socket, state, json_msg)

# ======== ======== ========




# ======== UDP Utilities ========

def broadcast_message(s: socket.socket, state: PeerState, message: str):
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    if TEST == 1:
        # Local test mode: simulate broadcast by looping through known ports
        for test_port in range(5000, 5010):
            s.sendto(message.encode(), ("127.0.0.1", test_port))
            print(f"[LOCAL BROADCAST] Sent to 127.0.0.1:{test_port}")
    else:
        # Real LAN broadcast
        s.sendto(message.encode(), ("255.255.255.255", state.udp_port))
        print(f"[LAN BROADCAST] Sent to 255.255.255.255:{state.udp_port}")

    print("Finished broadcast!")


def listen_for_messages(s: socket.socket, state: PeerState):
    print(f"[LISTENING] UDP messages on port {s.getsockname()[1]}")

    while True:
        try:
            data, addr = s.recvfrom(1024)
        except ConnectionResetError:
            continue
        message = data.decode()
        print(f"[UDP] From {addr}: {message}")

        try:
            msg = json.loads(message)
            if msg.get("type") == "peer_discovery":
                
                # ignore our own broadcast messages
                if addr[0] == state.host and addr[1] == state.port:
                    continue  

                print("     Peer verified, I will send my info!")

                response = peer_information_share(state.host, state.port)

                s.sendto(response.encode(), addr)
                print(f"     Sent info back to {addr[0]}:{addr[1]}")

            if msg.get("type") == "peer_info":
                peer_host = msg["host"]
                peer_port = msg["port"]
                if peer_host == state.host and peer_port == state.port:
                    continue
                
                print(f"     Peer {peer_host}:{peer_port} answered back, let's establish connection!")
                state.discovered_peers.put((peer_host, peer_port))

                
        except json.JSONDecodeError:
            #not json just ignore
            pass

# ======== ======== ========




# ======== UDP Handler ========

def peer_udp_handling(state: PeerState):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind((state.host, state.udp_port))

    # Start UDP listener thread
    threading.Thread(
        target=listen_for_messages,
        args=(udp_socket, state, ),
        daemon=True
    ).start()

    print("   Will Broadcast!")
    peer_discovery_broadcast(udp_socket, state)

    return udp_socket

# ======== ======== ========