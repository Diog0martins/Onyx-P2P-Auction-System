import json
from design.ui import UI
from crypto.encoding.b64 import b64d, b64e
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm
from crypto.crypt_decrypt.decrypt import decrypt_message_symmetric_gcm
from crypto.token.token_manager import verify_peer_blinding_data
from crypto.certificates.certificates import inspect_certificate
from client.ca_handler.ca_message import get_valid_timestamp
from client.message.auction.auction_handler import get_winning_key, remove_winning_key

def format_large_int(value):
    s = str(value)
    if len(s) > 10:
        return f"{s[:4]}...{s[-5:]}"
    return s

def get_client_identity(client_state, msg):
    auction_id = msg.get("auction_id")
    
    deal_key = get_winning_key(client_state.auctions, auction_id)

    if deal_key == None:
        UI.warn(f"Ignored identity reveal for auction {auction_id} (Not a winner).")
        return
    
    private_payload_crypted_json = msg.get("private_info")
    
    try:
        private_payload_json = decrypt_message_symmetric_gcm(
            private_payload_crypted_json, 
            deal_key
        )
        
        """
        "certificate": client_state.cert_pem
        """

        private_info_obj = json.loads(private_payload_json)
        winner_cert_pem = b64d(private_info_obj.get("certificate"))

        UI.sys("----- WINNER IDENTITY -----")
        inspect_certificate(winner_cert_pem)
        UI.sys("---------------------------")
        
        remove_winning_key(client_state.auctions, auction_id)
        UI.end_step("Auction Process", "COMPLETED")

    except Exception as e:
        UI.error(f"[SECURITY] GCM Decryption Failure (Private Content): {e}")
        return    

def send_winner_identity(client_state, auction_id, deal_key):
    
    private_payload_obj = {
        "certificate": b64e(client_state.cert_pem)
    }

    private_payload_json = json.dumps(private_payload_obj)
    private_payload = encrypt_message_symmetric_gcm(private_payload_json, deal_key)

    try:
        token_data = client_state.token_manager.get_token()
    except Exception as e:
        UI.error(f"Auction could not be created: {e}")
        return None

    timestamp = get_valid_timestamp()

    msg = {
        "type": "winner_revelation",
        "auction_id": auction_id,
        "token": token_data,
        "private_info": private_payload,
        "timestamp": timestamp
    }

    response_json = json.dumps(msg)
    c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

    from network.tcp import send_to_peers
    send_to_peers(c_response_json, client_state.peer.connections)    


def prepare_winner_identity(client_state, msg):
    
    auction_id = msg.get("auction_id")
    
    deal_key = get_winning_key(client_state.auctions, auction_id)

    if deal_key == None:
        UI.warn(f"Ignored owner revelation for auction {auction_id} (Not a winner).")
        return
    
    UI.step("Verifying Auction Owner", "PROCESSING")
    
    private_payload_crypted_json = msg.get("private_info")
    
    try:
        private_payload_json = decrypt_message_symmetric_gcm(
            private_payload_crypted_json, 
            deal_key
        )
        
        """
        "token_auction_id": token_id,
        "blinding_factor_r": r_value,
        "certificate": client_state.cert_pem
        """

        private_info_obj = json.loads(private_payload_json)

        revealed_token_id = private_info_obj.get("token_auction_id")
        r_reveald = private_info_obj.get("blinding_factor_r")
        auctioner_cert_pem = b64d(private_info_obj.get("certificate"))
        
        UI.success("Owner Announcement Decrypted")
        UI.sub_info(f"Auction Token ID: {revealed_token_id}")
        UI.sub_info(f"Blinding Factor 'r': {format_large_int(r_reveald)}")

        
        token_sig = client_state.ledger.find_token_signature(revealed_token_id)
        if not verify_peer_blinding_data(client_state.ca_pub_pem, client_state.uuid, revealed_token_id, r_reveald, token_sig):
            UI.sub_error("Owner verification failed.")
            return


        UI.sys("----- AUCTION OWNER IDENTITY -----")
        inspect_certificate(auctioner_cert_pem)
        UI.sys("----------------------------------")

    except Exception as e:
        UI.sub_security(f"GCM Decryption Failure (Private Content): {e}")
        return
    
    UI.sub_step("Action", "Sending Winner Identity")
    send_winner_identity(client_state, auction_id, deal_key)
    remove_winning_key(client_state.auctions, auction_id)
    UI.end_step("Identity Exchange", "COMPLETED")