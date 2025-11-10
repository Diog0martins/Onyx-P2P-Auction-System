#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from network.peer import run_peer
from network.config import parse_config


# ================================================================
# Configuration
# ================================================================

CONFIG_DIR = Path.cwd() / "user"
# CERT_FILE = CONFIG_DIR / "cert.pem"
# KEY_FILE = CONFIG_DIR / "private_key.pem"
# INFO_FILE = CONFIG_DIR / "info.json"
# Falta lista do host discover

# ================================================================
# Keys
# ================================================================

def generate_key_pair():
    """Generate RSA private/public key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Convert private key to PEM
    private_pem = private_key.private_bytes(
        encoding = serialization.Encoding.PEM,
        format = serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm = serialization.NoEncryption()
    )

    # Convert public key to PEM
    public_pem = private_key.public_key().public_bytes(
        encoding = serialization.Encoding.PEM,
        format = serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem

# ================================================================
# Dir, Load, Save 
# ================================================================

def ensure_config_dir():
    """Create the directory if it does not exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_info():
    """Load the information of the user"""
    info_file = CONFIG_DIR / "info.json"
    if info_file.exists():
        with info_file.open("r") as f:
            return json.load(f)
    return {}

def save_info(data):
    """Save the info of the user"""
    info_file = CONFIG_DIR / "info.json"
    with info_file.open("w") as f:
        json.dump(data, f, indent=4)



# ================================================================
# Informations
# ================================================================

# def ask_money():
#     while True:
#         val = input("> ").strip()
#         try:
#             return int(val)   # tem de ser um numero
#         except ValueError:
#             print("Not a number, try again")


def create_info(args):
    user = {}
    print("Name:")
    user["name"] = input("> ").strip()
    print("Pass:")
    user["pass"] = input("> ").strip()
    print("Direction:")
    user["Direction"] = input("> ").strip()
    # print("Money:")
    # user["Money"] = ask_money()

    # user_dir = CONFIG_DIR / user["name"]
    # user_dir.mkdir(parents=True, exist_ok=True)

    # Crio o par chaves
    private_pem, public_pem = generate_key_pair()
    (CONFIG_DIR / "private_key.pem").write_bytes(private_pem)
    (CONFIG_DIR / "public_key.pem").write_bytes(public_pem)

    # Mando a public key ao CA


    # Recevo o certificado


    # Guardo o certificado na pasta


    # HOST DISCOVER

    if len(args) == 2:
        # Local Testing Use Config Files
        print("Peer info fetched from config file")

        

        host, port = parse_config(sys.argv[1])
    else: 
        #LAN Case -> For the Future
        print("LAN Case: Not implemented!")
        sys.exit(1)

    run_peer(host, port)

    save_info(user)



# ================================================================
# Menus
# ================================================================



def start_client(args):
    ensure_config_dir()
    user = load_info()
    if user == {}:
        create_info(args)
