#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from network.peer import run_peer_test
from network.config import parse_config
from client.info.info_handler import load_info, save_info_test, create_info
from client.keys.keys_handler import generate_key_pair


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
    if len(args) == 2:
        ensure_config_dir_test(args[1])
    user = load_info(args[1])

    if user == {}:
        user = create_info()

    # Mando a public key ao CA


    # Receber o certificado



    if len(args) == 2:
        # Local Testing Use Config Files
        print("Peer info fetched from config file")
        host, port = parse_config(sys.argv[1])
        # Crio o par chaves
        private_pem, public_pem = generate_key_pair()
        (CONFIG_DIR / args[1] / "private_key.pem").write_bytes(private_pem)
        (CONFIG_DIR / args[1] / "public_key.pem").write_bytes(public_pem)

        # Guardo o certificado na pasta


        save_info_test(user, args[1])

        # HOST DISCOVER
        run_peer_test(host, port, args[1])
    else: 
        #LAN Case -> For the Future
        print("LAN Case: Not implemented!")
        sys.exit(1)

    # run_peer(host, port)
