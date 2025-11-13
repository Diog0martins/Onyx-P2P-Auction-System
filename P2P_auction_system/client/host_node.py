#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from network.peer import run_peer_test
from config.config import parse_config
from client.info.info_handler import load_info, save_info_test#, create_info
from crypto.keys.keys_handler import generate_key_pair
from client.client_state import Client 

from client.ca_handler.ca_connection import connect_and_register_to_ca

# ================================================================
# Configuration
# ================================================================

CONFIG_DIR = Path.cwd() / "config"
# CERT_FILE = CONFIG_DIR / "cert.pem"
# KEY_FILE = CONFIG_DIR / "private_key.pem"
# INFO_FILE = CONFIG_DIR / "info.json"
# Falta lista do host discover

def ensure_config_dir_test(argv):
    """Create the directory if it does not exist."""
    (CONFIG_DIR / argv).mkdir(parents=True, exist_ok=True)

def start_client(args):
    # if user == {}:
    #     user = create_info()

    # Mando a public key ao CA
    info = connect_and_register_to_ca("client-teste")
    print(json.dumps({
        "uid": info["uid"],
        "cert": info["cert"],
    }, indent=4))


    # Receber o certificado



    if len(args) == 2:
        # Local Testing Use Config Files
        ensure_config_dir_test(args[1])
        load = load_info(args[1])

        if load != {}:
            userID = load["userID"]
            public_key = load.get("public_key", "")
            private_key = load.get("private_key", "")

            if public_key == "" or private_key == "":
                private_pem, public_pem = generate_key_pair()
                (CONFIG_DIR / args[1] / "private_key.pem").write_bytes(private_pem)
                (CONFIG_DIR / args[1] / "public_key.pem").write_bytes(public_pem)
                load["public_key"] = public_pem.decode()
                load["private_key"] = private_pem.decode()
                public_key = public_pem
                private_key = private_pem
                save_info_test(load, args[1])
        
        #falta o else mas segundo entendi este ficheiro sempre vai estar

        client = Client(userID, public_key, private_key)
        # o que fazo com ele agora :(

        # Guardo o certificado na pasta

        # HOST DISCOVER
        print("Peer info fetched from config file")
        host, port = parse_config(args[1]) #sys.argv[1]
        run_peer_test(host, port, args[1])
    else: 
        #LAN Case -> For the Future
        print("LAN Case: Not implemented!")
        sys.exit(1)

    # run_peer(host, port)
