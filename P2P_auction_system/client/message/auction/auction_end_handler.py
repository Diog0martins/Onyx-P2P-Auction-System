import json
import time
import secrets
from design.ui import UI
from datetime import datetime
from crypto.encoding.b64 import b64e
from crypto.keys.keys_crypto import generate_aes_key
from crypto.crypt_decrypt.hybrid import hybrid_encrypt
from client.ca_handler.ca_message import get_valid_timestamp
from client.message.auction.auction_handler import add_winning_key
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm, encrypt_with_public_key


def handle_auction_end(client_state, obj):
    """
    Processes the 'auctionEnd' event. It notifies the user via CLI and, if the local user 
    is the winner, initiates the cryptographic identity reveal protocol (Proof of Winning).
    """
    from network.tcp import send_to_peers
    now = int(time.time())

    auction_list = client_state.auctions["auction_list"]
    auction_target = obj.get('auction_id')
    info = auction_list.get(auction_target)

    if info is None:
        UI.warn(f"AUCTION_END received for unknown auction {auction_target}")
        return

    # UI Notification
    closing_timestamp = info.get("closing_date")
    closing_dt = datetime.fromtimestamp(closing_timestamp)
    
    print()
    UI.sys("--- AUCTION CLOSING NOTICE ---")
    UI.info(f"AUCTION CLOSED: ID {auction_target}")
    UI.info(f"Time to Close Registered: {closing_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    UI.info(f"Current Time: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    UI.sys("-----------------------------------")
    print()

    # Check if I am the winner
    if info.get("my_bid") == 'True':

        my_winning_token = info.get("last_bid_token_data")

        if my_winning_token:
            token_id = my_winning_token.get("token_id")

            if token_id:
                UI.step("Processing Winner Status", "STARTED")
                
                # 1. Retrieve Unblinding Factor 'r' (Proof of Ownership)
                r_value = client_state.token_manager.get_blinding_factor_r(token_id)
                if r_value is None:
                    UI.error(f"Critical Error: Token ID {token_id} not found in local wallet.")
                    return

                # 2. Generate and Encrypt Session Key (Deal Key)
                deal_key = generate_aes_key()
                add_winning_key(client_state.auctions, auction_target, deal_key)

                private_payload_obj = {
                    "token_winner_bid_id": token_id,
                    "blinding_factor_r": r_value,
                }

                # Encrypt Proof with Deal Key (Symmetric)
                private_payload_json = json.dumps(private_payload_obj)
                private_payload = encrypt_message_symmetric_gcm(private_payload_json, deal_key)

                # Encrypt Deal Key with Auction Public Key (Asymmetric)
                auction_public_key = info.get("public_key")
                deal_key_encrypted_bytes = encrypt_with_public_key(deal_key, auction_public_key.encode('utf-8'))
                deal_key_encrypted_b64 = b64e(deal_key_encrypted_bytes)

                # 3. Prepare New Token for Anonymous Transmission
                try:
                    token_data = client_state.token_manager.get_token()
                except Exception as e:
                    UI.error(f"Unable to create Auction Token: {e}")
                    return None

                # 4. Create Encrypted Identity Package (Accountability)
                identity_pkg = {
                    "real_uid": client_state.uuid,
                    "cert_pem_b64": b64e(client_state.cert_pem) if isinstance(client_state.cert_pem, bytes) else client_state.cert_pem,
                    "token_id_bound": token_data["token_id"],
                    "nonce": secrets.token_hex(16)
                }
                encrypted_identity_blob = hybrid_encrypt(identity_pkg, client_state.ca_pub_pem)
                timestamp = get_valid_timestamp()

                # 5. Construct & Broadcast Message
                public_payload_obj = {
                    "type": "winner_token_reveal",
                    "auction_id": auction_target,
                    "token": token_data,
                    "deal_key": deal_key_encrypted_b64,
                    "private_info": private_payload,
                    "encrypted_identity": encrypted_identity_blob,
                    "timestamp": timestamp,
                }

                response_json = json.dumps(public_payload_obj)
                c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

                UI.sub_step("Action", "Submitting blind factor 'r' revelation")
                send_to_peers(c_response_json, client_state.peer.connections)
                UI.end_step("Winner Token Reveal", "SENT")

            else:
                UI.error("Token ID not found.")
                return
        else:
            UI.error("Auction ended without a winner token in the data.")
    else:
        return