#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

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

def load_ledger():
    ledger_file = CONFIG_DIR / "ledger.json"
    if ledger_file.exists():
        with ledger_file.open("r") as f:
            return json.load(f)
    return []

def save_ledger(ledger):
    ledger_file = CONFIG_DIR / "ledger.json"
    with ledger_file.open("w") as f:
        json.dump(ledger, f, indent=4)

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


def create_info():
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


    save_info(user)

# ================================================================
# Commands
# ================================================================

def cmd_bid():
    ledger = load_ledger()

    # Filter auctions NOT owned by this user
    auctions = [entry for entry in ledger if "id" in entry and entry.get("owner") != "me" and entry.get("type") == "auction"]

    if not auctions:
        print("No available auctions (not yours).")
        return

    print("\nAvailable auctions:")
    for a in auctions:
        print(f"ID {a['id']} | {a['name']} | min bid: {a['min_bid']}")

    # Make sure auction exists
    auction = None
    while True:
        try:
            target = int(input("\nSelect auction ID: ").strip())
        except ValueError:
            print("Invalid number.")
            continue    

        auction = next((x for x in auctions if x.get("id") == target), None)
        if auction:
            break
        else:
            print("Auction not found or not allowed. Try again.")


    # Enter bid amount
    while True:
        try:
            bid = float(input("Bid amount: ").strip())
        except ValueError:
            print("Invalid number.")
            continue

        if bid < auction["min_bid"]:
            print(f"Bid must be >= {auction['min_bid']}")
            continue

        break

    # Generate progressive bid ID
    bid_id = max(item.get("id", 0) for item in ledger) + 1

    # Full bid stored locally
    bid_obj_local = {
        "id": bid_id,
        "type": "bid",
        "auction_id": target,
        "bid": bid,
        "bidder": "me"
    }

    # JSON safe for network
    bid_obj_public = {
        "id": bid_id,
        "type": "bid",
        "auction_id": target,
        "bid": bid
    }

    ledger.append(bid_obj_local)
    save_ledger(ledger)

    print()
    print(f"Bid created with ID {bid_id}")

    bid_json = json.dumps(bid_obj_public)

    print("JSON ready to broadcast:")
    print(bid_json)
    print()

    ##############################################################
    # TODO: broadcast bid_json to all users                      #
    ##############################################################

    menu_user()


def cmd_auction():
    # Ask for auction object
    auction_object = input("Auction object: ").strip()
    if not auction_object:
        print("Invalid name.")
        return

    # Ask for minimum bid
    try:
        min_bid = float(input("Minimum bid: ").strip())
    except ValueError:
        print("Invalid number.")
        return

    # Load existing ledger
    ledger = load_ledger()

    # Generate progressive auction_id
    if len(ledger) == 0:
        auction_id = 1
    else:
        # Get the LAST id among auctions
        auction_id = max(item.get("id", 0) for item in ledger) + 1

    # Full auction object stored privately
    auction_obj_local = {
        "id": auction_id,
        "type": "auction",
        "name": auction_object,
        "min_bid": min_bid,
        "owner": "me"       # <-- PRIVATE INFO
    }

    # Broadcast version (no owner)
    auction_obj_public = {
        "id": auction_id,
        "type": "auction",
        "name": auction_object,
        "min_bid": min_bid,
    }

    # Save locally
    ledger.append(auction_obj_local)
    save_ledger(ledger)

    print()
    print(f"Auction created with ID {auction_id}")

    # JSON ready to send
    auction_json = json.dumps(auction_obj_public)

    print("JSON ready to broadcast:")
    print(auction_json)
    print()

    ##########################################################
    # TODO: broadcast auction_json to other users            #
    ##########################################################

    menu_user()


def cmd_status():

    user = load_info()
    print("====== USER INFO ======")
    for k, v in user.items():
        print(f"{k.capitalize():>10}: {v}")
    print("=======================\n")

def cmd_exit():
    print("Exiting...")
    sys.exit(0)

# ================================================================
# Menus
# ================================================================

def menu_user():
    print("Available commands:")
    print(" /bid")
    print(" /auction")
    print(" /status")
    print(" /exit\n")

    user_input = input("> ").strip()
    print()

    if user_input == "bid":
        cmd_bid()
    elif user_input == "auction":
        cmd_auction()
    elif user_input == "status":
        cmd_status()
    elif user_input == "exit":
        cmd_exit()
    else:
        print("Unknown command.")
    menu_user()

def main():
    ensure_config_dir()
    user = load_info()
    if user == {}:
        create_info()
    menu_user()

if __name__ == "__main__":
    main()