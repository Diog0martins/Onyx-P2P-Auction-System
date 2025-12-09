import threading, queue

class PeerState:
    def __init__(self, host, port, udp_port=None):
        """
                Initializes the network state of a peer.
                Stores host/port info, manages active connections, and handles thread synchronization events.
        """

        self.host = host
        self.port = port
        # self.udp_port = udp_port or port
        self.discovered_peers = queue.Queue()
        self.connections = []
        self.stop_event = threading.Event()
