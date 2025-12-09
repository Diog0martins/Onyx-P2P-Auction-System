import json
from design.ui import UI
from crypto.encoding.b64 import b64d, b64e
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm
from client.message.auction.auction_handler import add_winning_key
from crypto.token.token_manager import verify_peer_blinding_data
from client.ca_handler.ca_message import get_valid_timestamp
from crypto.crypt_decrypt.decrypt import decrypt_with_private_key, decrypt_message_symmetric_gcm
from client.message.winner_reveal.final_revelation import format_large_int

def send_auction_creation_proof(client_state, auction_id, deal_key):

    auction_list = client_state.auctions["auction_list"]
    info = auction_list.get(auction_id)

    # Get token used to create the auction
    auction_token = info.get("auction_token_data")
    
    # Prepare proof that token is owned by user
    if auction_token:

        token_id = auction_token.get("token_id")
        
        if token_id:                    
            r_value = client_state.token_manager.get_blinding_factor_r(token_id)

            if r_value is None:
                UI.error(f"Critical Error: Token ID {token_id} not found in local wallet.")
                return

            private_payload_obj = {
                "token_auction_id": token_id,
                "blinding_factor_r": r_value,
                "certificate": b64e(client_state.cert_pem)
            }

            private_payload_json = json.dumps(private_payload_obj)
            private_payload = encrypt_message_symmetric_gcm(private_payload_json, deal_key)

            try:
                token_data = client_state.token_manager.get_token()
            except Exception as e:
                UI.error(f"Unable to create Auction Token: {e}")
                return None

            timestamp = get_valid_timestamp()

            msg = {
                "type": "auction_owner_revelation",
                "auction_id": auction_id,
                "token": token_data,
                "private_info": private_payload,
                "timestamp": timestamp
            }

            response_json = json.dumps(msg)
            c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

            UI.sub_step("Action", "Submitting blind factor 'r' disclosure")
            from network.tcp import send_to_peers
            send_to_peers(c_response_json, client_state.peer.connections)


def handle_winner_reveal(client_state, obj):

    auction_id = obj.get("auction_id")
    
    my_auction = client_state.auctions["my_auctions"].get(auction_id)
    
    if my_auction is None:
        UI.error(f"Received WINNER_REVEAL for auction {auction_id} that does not belong to me.")
        return

    UI.step(f"Verifying Winner Claim (ID: {auction_id})", "PROCESSING")

    my_auction_private_key_pem = my_auction.get("private_key")
    
    if my_auction_private_key_pem is None:
        return

    cleaned_pem_string = my_auction_private_key_pem.strip()
    private_key_pem_bytes = cleaned_pem_string.encode('utf-8') 
    
    deal_key_encrypted_b64 = obj.get("deal_key")

    try:
        deal_key_encrypted_bytes = b64d(deal_key_encrypted_b64)
    except Exception as e:
        UI.sub_error(f"Failed to decode encrypted Deal Key Base64: {e}")
        return
    
    try:
        deal_key_bytes = decrypt_with_private_key(
            deal_key_encrypted_bytes, 
            private_key_pem_bytes
        )
    except Exception as e:
        UI.sub_security(f"RSA Decryption Failure (Deal Key): {e}")
        return
    

    private_payload_crypted_json = obj.get("private_info")
    
    try:
        private_payload_json = decrypt_message_symmetric_gcm(
            private_payload_crypted_json, 
            deal_key_bytes
        )
        
        private_info_obj = json.loads(private_payload_json)
        
        revealed_token_id = private_info_obj.get("token_winner_bid_id")
        r_reveald = private_info_obj.get("blinding_factor_r")
        
        UI.success("Winner Announcement Decrypted")
        UI.sub_info(f"Winner Token ID: {revealed_token_id}")
        UI.sub_info(f"Blinding Factor 'r': {format_large_int(r_reveald)}")

        
        token_sig = client_state.ledger.find_token_signature(revealed_token_id)
        if not verify_peer_blinding_data(client_state.ca_pub_pem, client_state.uuid, revealed_token_id, r_reveald, token_sig):
            UI.sub_error("Winner verification failed.")
            return
    
    except Exception as e:
        UI.sub_security(f"GCM Decryption Failure (Private Content): {e}")
        return
    
    add_winning_key(client_state.auctions, auction_id, deal_key_bytes)
    send_auction_creation_proof(client_state, auction_id, deal_key_bytes)
    UI.end_step("Auction Owner Proof", "SENT")