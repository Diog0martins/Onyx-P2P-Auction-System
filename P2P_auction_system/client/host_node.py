import sys
import json
import os
from pathlib import Path
from network.peer import run_peer_test
from network.ip import get_ip
from config.config import parse_config
from crypto.keys.keys_handler import prepare_key_pair_generation
from client.client_state import Client 
from client.ca_handler.ca_connection import connect_and_register_to_ca


CONFIG_DIR = Path.cwd() / "config"


def ensure_config_dir_test(argv):
    (CONFIG_DIR / argv).mkdir(parents=True, exist_ok=True)


def check_user_path(user_path):
    if not user_path.exists():
        user_path.mkdir(parents=True, exist_ok=True)

def start_client(args):

    # Verify if we are working in LAN or localhost
    if len(args) == 2:
        config = args[1]
        user_path = Path("config") / config / "user"
        print("Peer info fetched from config file")
        user_id, host, port = parse_config(config)
    
    else: 
        #LAN Case -> For the Future
        user_path = Path("/user")
        host = get_ip()
        port = 6000
        print("LAN Case: Not implemented!")

    check_user_path(user_path)

    # Generate or get key pair for further validation[ /user folder]
    private_key, public_key = prepare_key_pair_generation(user_path)

    # Generate Client Object
    client = Client(user_id, public_key, private_key)

    # Send public key ao CA
    info = connect_and_register_to_ca(client)

    client.cert_pem = info["cert_pem"]
    client.ca_pub_pem = info["ca_pub_pem"]

    # Host Discovery and Connection Establishment
    run_peer_test(host, port, args[1])


