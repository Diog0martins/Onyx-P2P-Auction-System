import sys
import config
from peer import run_peer

def open_connection():

    if len(sys.argv) == 2:
        # Local Testing Use Config Files
        print("Peer info fetched from config file")
        host, port = config.parse_config(sys.argv[1])
    else: 
        #LAN Case -> For the Future
        print("LAN Case: Not implemented!")
        sys.exit(1)

    run_peer(host, port)

def main():
    open_connection()

if __name__ == "__main__":
    main()