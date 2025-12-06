from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm
from crypto.crypt_decrypt.decrypt import decrypt_message_symmetric_gcm
import json
from crypto.encoding.b64 import b64d, b64e
from client.message.auction.auction_handler import get_winning_key, remove_winning_key
from crypto.token.token_manager import verify_peer_blinding_data
from crypto.certificates.certificates import inspect_certificate

def get_client_identity(client_state, msg):
    auction_id = msg.get("auction_id")
    
    deal_key = get_winning_key(client_state.auctions, auction_id)

    if deal_key == None:
        print(f"You did not win auction {auction_id}")
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

        print("=====     Winner Identity     =====")
        inspect_certificate(winner_cert_pem)
        print("= ===== ==== ==== ==== ==== ===== =")
        
        remove_winning_key(client_state.auctions, auction_id)

    except Exception as e:
        print(f"[SECURITY] GCM Decryption Failure (Private Content): {e}")
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
        print(f"[!] Auction could not be created: {e}")
        return None

    msg = {
        "type": "winner_revelation",
        "auction_id": auction_id,
        "token": token_data,
        "private_info": private_payload
    }

    response_json = json.dumps(msg)
    c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

    from network.tcp import send_to_peers
    send_to_peers(c_response_json, client_state.peer.connections)    


def prepare_winner_identity(client_state, msg):
    
    auction_id = msg.get("auction_id")
    
    deal_key = get_winning_key(client_state.auctions, auction_id)

    if deal_key == None:
        print(f"You did not win auction {auction_id}")
        return
    
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
        
        print("\n=== Winner announcement processed ===")
        print(f"Auction Token id: {revealed_token_id}")
        print(f"Blinding Factor 'r': {r_reveald}")

        
        token_sig = client_state.ledger.find_token_signature(revealed_token_id)
        if not verify_peer_blinding_data(client_state.ca_pub_pem, client_state.uuid, revealed_token_id, r_reveald, token_sig):
            return


        print("===== Auction Owner Identity =====")
        inspect_certificate(auctioner_cert_pem)
        print("= ===== ==== ==== ==== ==== ===== =")

    except Exception as e:
        print(f"[SECURITY] GCM Decryption Failure (Private Content): {e}")
        return
    
    send_winner_identity(client_state, auction_id, deal_key)
    remove_winning_key(client_state.auctions, auction_id)