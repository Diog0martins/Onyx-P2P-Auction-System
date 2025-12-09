import sys
from client.host_node import start_client

def main():
    """
        Main entry point for the Client Application.
        Passes command-line arguments to the host node starter to initialize the peer.
    """

    start_client(sys.argv)

if __name__ == "__main__":
    main()