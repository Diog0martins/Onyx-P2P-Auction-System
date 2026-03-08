import socket
import json
import time
import sys
import os
from pathlib import Path

# Add the project root to the path to import the architecture modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.client_state import Client
from crypto.keys.keys_handler import prepare_key_pair_generation
from client.ca_handler.ca_connection import connect_and_register_to_ca
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm
from crypto.token.token_manager import TokenManager
from client.ca_handler.ca_message import get_valid_timestamp

RELAY_HOST = '127.0.0.1'
RELAY_PORT = 6000

def setup_stealth_attacker():
    """Registers the attacker, creates a real TokenManager, and connects to the Relay."""
    print("[*] 1. Registering the Attacker (Insider Threat) with the CA...")
    user_path = Path("config/attacker_poc/user")
    user_path.mkdir(parents=True, exist_ok=True)
    
    private_key, public_key = prepare_key_pair_generation(user_path)
    attacker_client = Client(user_path, public_key, private_key)
    
    try:
        # Obtain certificates and Group Key
        info = connect_and_register_to_ca(attacker_client)
        attacker_client.uuid = info["uid"]
        attacker_client.group_key = info["group_key"]
        attacker_client.ca_pub_pem = info["ca_pub_pem"]
        
        # Initialize the attacker's TokenManager to request real tokens
        attacker_client.token_manager = TokenManager("attacker_poc", attacker_client.ca_pub_pem, attacker_client.uuid)
        
        print(f"[*] 2. Establishing stealth connection with the Relay ({RELAY_HOST}:{RELAY_PORT})...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((RELAY_HOST, RELAY_PORT))
        
        # The Relay requires the UUID as the first message
        s.sendall((attacker_client.uuid + "\n").encode('utf-8'))
        print("[+] Connection established and kept open!")
        
        return attacker_client, s
    except Exception as e:
        print(f"[-] Setup error. Are the CA and Relay running? Error: {e}")
        sys.exit(1)

def build_and_send(payload, attacker_client, persistent_socket):
    """Encrypts and injects the message into the Relay."""
    payload_json = json.dumps(payload)
    encrypted_msg = encrypt_message_symmetric_gcm(payload_json, attacker_client.group_key)
    persistent_socket.sendall((encrypted_msg + "\n").encode('utf-8'))

def attack_invalid_signature(attacker, s):
    print("\n[+] Attack 1: Invalid Signature (Spoofing)")
    print("   -> Requesting a legitimate token from the CA...")
    token_data = attacker.token_manager.get_token()
    
    print("   -> Corrupting the token signature (altering the last bytes)...")
    # Corrupts the signature so the RSA math fails on the Peer
    token_data["token_sig"] = token_data["token_sig"][:-5] + "XXXXX"
    
    payload = {
        "id": 1111,
        "type": "bid",
        "auction_id": 1,
        "bid": 500,
        "token": token_data,
        "timestamp": get_valid_timestamp()
    }
    build_and_send(payload, attacker, s)
    print("   [+] Malicious payload injected into the network!")

def attack_token_reuse(attacker, s):
    print("\n[+] Attack 2: Token Reuse (Double Spending)")
    print("   -> Requesting a fresh, legitimate token from the CA...")
    token_data = attacker.token_manager.get_token()
    
    payload = {
        "id": 2222,
        "type": "bid",
        "auction_id": 1,
        "bid": 600,
        "token": token_data,
        "timestamp": get_valid_timestamp()
    }
    
    print("   -> Sending 1st time (Legitimate message, will be saved in the Ledger)...")
    build_and_send(payload, attacker, s)
    
    time.sleep(1.5) # Gives the target Peer time to process and write to the Ledger
    
    print("   -> Sending 2nd time (Replay Attack, will trigger the alarm!)...")
    payload["id"] = 2223 # Change the msg ID to look different, but the token is the same
    payload["timestamp"] = get_valid_timestamp()
    build_and_send(payload, attacker, s)

def attack_ledger_tampering(attacker, s):
    print("\n[+] Attack 3: Ledger Tampering (Desynchronization)")
    print("   -> Creating a malicious blockchain with fake hashes...")
    
    fake_ledger = {
        "chain": [
            {"height": 0, "prev_hash": "0", "timestamp": "2026", "events": [], "block_hash": "hash_genesis_ok"},
            {"height": 1, "prev_hash": "hash_genesis_ok", "timestamp": "2026", "events": [], "block_hash": "HASH_FALSO_QUE_QUEBRA_CONSENSO"}
        ],
        "current_actions": [],
        "max_actions": 1
    }
    
    payload = {
        "request_id": 3333,
        "type": "ledger_update",
        "ledger": fake_ledger,
        "token": attacker.token_manager.get_token(),
        "timestamp": get_valid_timestamp()
    }
    build_and_send(payload, attacker, s)
    print("   [+] Poisoned blockchain injected into the network!")

def main():
    # Starts the attacker in stealth mode
    attacker_client, persistent_socket = setup_stealth_attacker()
    
    try:
        while True:
            print("\n" + "="*50)
            print("   PEER NODE ATTACK SIMULATOR (INSIDER)   ")
            print("="*50)
            print("1. Execute Invalid Signature (Message Spoofing)")
            print("2. Execute Token Reuse (Double Spending)")
            print("3. Execute Ledger Tampering (Eclipse Attack)")
            print("4. Exit (Gracefully disconnects from the Relay)")
            
            choice = input("\nChoose an attack (1-4): ")
            
            if choice == '1':
                attack_invalid_signature(attacker_client, persistent_socket)
            elif choice == '2':
                attack_token_reuse(attacker_client, persistent_socket)
            elif choice == '3':
                attack_ledger_tampering(attacker_client, persistent_socket)
            elif choice == '4':
                print("\nExiting... The socket will be closed and the CA will rotate the group key!")
                break
            else:
                print("Invalid option.")
    finally:
        persistent_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    main()
