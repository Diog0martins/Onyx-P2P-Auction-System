import socket
import json
import time
import sys
import os
from pathlib import Path

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
    print("[*] 1. A registar o Atacante (Insider Threat) na CA...")
    user_path = Path("config/attacker_poc/user")
    user_path.mkdir(parents=True, exist_ok=True)
    
    private_key, public_key = prepare_key_pair_generation(user_path)
    attacker_client = Client(user_path, public_key, private_key)
    
    try:
        info = connect_and_register_to_ca(attacker_client)
        attacker_client.uuid = info["uid"]
        attacker_client.group_key = info["group_key"]
        attacker_client.ca_pub_pem = info["ca_pub_pem"]
        
        attacker_client.token_manager = TokenManager("attacker_poc", attacker_client.ca_pub_pem, attacker_client.uuid)
        
        print(f"[*] 2. A estabelecer conexão furtiva com o Relay ({RELAY_HOST}:{RELAY_PORT})...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((RELAY_HOST, RELAY_PORT))
        
        # O Relay exige o UUID como primeira mensagem
        s.sendall((attacker_client.uuid + "\n").encode('utf-8'))
        print("[+] Conexão estabelecida e mantida aberta!")
        
        return attacker_client, s
    except Exception as e:
        print(f"[-] Erro no setup. A CA e o Relay estão a correr? Erro: {e}")
        sys.exit(1)

def build_and_send(payload, attacker_client, persistent_socket):
    payload_json = json.dumps(payload)
    encrypted_msg = encrypt_message_symmetric_gcm(payload_json, attacker_client.group_key)
    persistent_socket.sendall((encrypted_msg + "\n").encode('utf-8'))

def attack_invalid_signature(attacker, s):
    print("\n[+] Ataque 1: Invalid Signature (Spoofing)")
    print("   -> A pedir um token legítimo à CA...")
    token_data = attacker.token_manager.get_token()
    
    print("   -> A corromper a assinatura do token (alterando os últimos bytes)...")
    # Corrompe a assinatura para que a matemática RSA falhe no Peer
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
    print("   [+] Payload malicioso injetado na rede!")

def attack_token_reuse(attacker, s):
    print("\n[+] Ataque 2: Token Reuse (Double Spending)")
    print("   -> A pedir um token legítimo e fresco à CA...")
    token_data = attacker.token_manager.get_token()
    
    payload = {
        "id": 2222,
        "type": "bid",
        "auction_id": 1,
        "bid": 600,
        "token": token_data,
        "timestamp": get_valid_timestamp()
    }
    
    print("   -> A enviar a 1ª vez (Mensagem legítima, será guardada no Ledger)...")
    build_and_send(payload, attacker, s)
    
    time.sleep(1.5)
    
    print("   -> A enviar a 2ª vez (Replay Attack, vai disparar o alarme!)...")
    payload["id"] = 2223
    payload["timestamp"] = get_valid_timestamp()
    build_and_send(payload, attacker, s)

def attack_ledger_tampering(attacker, s):
    print("\n[+] Ataque 3: Ledger Tampering (Desynchronization)")
    print("   -> A criar uma blockchain maliciosa com hashes falsos...")
    
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
    print("   [+] Blockchain envenenada injetada na rede!")

def main():
    attacker_client, persistent_socket = setup_stealth_attacker()
    
    try:
        while True:
            print("\n" + "="*50)
            print("   SIMULADOR DE ATAQUES AO PEER NODE (INSIDER)   ")
            print("="*50)
            print("1. Executar Invalid Signature (Message Spoofing)")
            print("2. Executar Token Reuse (Double Spending)")
            print("3. Executar Ledger Tampering (Eclipse Attack)")
            print("4. Sair (Desconecta graciosamente do Relay)")
            
            opcion = input("\nEscolhe um ataque (1-4): ")
            
            if opcion == '1':
                attack_invalid_signature(attacker_client, persistent_socket)
            elif opcion == '2':
                attack_token_reuse(attacker_client, persistent_socket)
            elif opcion == '3':
                attack_ledger_tampering(attacker_client, persistent_socket)
            elif opcion == '4':
                print("\nSaindo... O socket será fechado e a CA vai rodar a chave de grupo!")
                break
            else:
                print("Opção inválida.")
    finally:
        persistent_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    main()
