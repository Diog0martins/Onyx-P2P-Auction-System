from cryptography.hazmat.primitives import serialization
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm, encrypt_with_public_key
from datetime import datetime
import json
import time
from crypto.encoding.b64 import b64e
from crypto.keys.keys_crypto import generate_aes_key
from client.message.auction.auction_handler import add_winning_key

def handle_auction_end(client_state, obj):
    from network.tcp import send_to_peers
    now = int(time.time())

    auction_list = client_state.auctions["auction_list"]
    auction_target = obj.get('auction_id')
    info = auction_list.get(auction_target)

    if info is None:
        print(f"[INFO] AUCTION_END received for unknown auction {auction_target}")
        return

    closing_timestamp = info.get("closing_date")
    closing_dt = datetime.fromtimestamp(closing_timestamp)
    print(f"\n--- 🔔 AUCTION CLOSING NOTICE ---")
    print(f"AUCTION CLOSED: ID {auction_target}")
    print(f"Time to Close Regitada: {closing_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current Time: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"-----------------------------------\n")

    # If USer consideres himself the winner
    if info.get("my_bid") == 'True':
        
        # Get token used the last bid
        my_winning_token = info.get("last_bid_token_data")
        
        # Prepare proof that token is owned by user
        if my_winning_token:

            token_id = my_winning_token.get("token_id")
            
            if token_id:                    
                r_value = client_state.token_manager.get_blinding_factor_r(token_id)

                if r_value is None:
                    print(f"[!] Critical Error: Token ID {token_id} not found in local wallet.")
                    return

                deal_key = generate_aes_key()
                add_winning_key(client_state.auctions, auction_target, deal_key)

                private_payload_obj = {
                    "token_winner_bid_id": token_id,
                    "blinding_factor_r": r_value,
                }

                private_payload_json = json.dumps(private_payload_obj)
                private_payload = encrypt_message_symmetric_gcm(private_payload_json, deal_key)

                auction_public_key = info.get("public_key")
                deal_key_encrypted_bytes = encrypt_with_public_key(deal_key, auction_public_key.encode('utf-8'))
                deal_key_encrypted_b64 = b64e(deal_key_encrypted_bytes)

                try:
                    token_data = client_state.token_manager.get_token()
                except Exception as e:
                    print(f"[!] Unable to create Auction: {e}")
                    return None

                public_payload_obj = {
                    "type": "winner_token_reveal", 
                    "auction_id": auction_target,
                    "token": token_data,
                    "deal_key": deal_key_encrypted_b64,
                    "private_info": private_payload
                }

                response_json = json.dumps(public_payload_obj)
                c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

                print(f"[WINNER] Submitting blind factor “r” revelation for auction {auction_target}...")
                send_to_peers(c_response_json, client_state.peer.connections)
            
            else:
                print("[ERROR] Token ID not found.")
                return
            
        else:
            print("[ERROR] Auction ended without a winner token in the data.")
    else:
        return