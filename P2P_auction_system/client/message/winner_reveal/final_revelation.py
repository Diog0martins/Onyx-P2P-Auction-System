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
    """
    Helper function to truncate large integers for display (e.g., blinding factors).
    """
    s = str(value)
    if len(s) > 10:
        return f"{s[:4]}...{s[-5:]}"
    return s

def get_client_identity(client_state, msg):
    """
    Handles the receipt of the winner's identity by the auction owner.
    
    This function decrypts the 'private_info' payload using the session 'deal_key'.
    It extracts the winner's X.509 certificate and displays it, completing the auction lifecycle.

    Args:
        client_state: The main client state object containing auction data and UI handlers.
        msg (dict): The message received from the network containing the winner's revelation.
    """
    auction_id = msg.get("auction_id")
    
    # Retrieve the symmetric session key established for this specific deal/auction
    deal_key = get_winning_key(client_state.auctions, auction_id)

    if deal_key == None:
        UI.warn(f"Ignored identity reveal for auction {auction_id} (Not a winner).")
        return
    
    # The sensitive identity data is nested inside 'private_info', encrypted with the deal_key
    private_payload_crypted_json = msg.get("private_info")
    
    try:
        # Decrypt the private payload using AES-GCM (ensures confidentiality and integrity)
        private_payload_json = decrypt_message_symmetric_gcm(
            private_payload_crypted_json, 
            deal_key
        )
        
        # Expected JSON Structure:
        # {
        #    "certificate": <Base64 encoded PEM certificate of the winner>
        # }

        private_info_obj = json.loads(private_payload_json)
        winner_cert_pem = b64d(private_info_obj.get("certificate"))

        # Display the Verified Identity of the Winner
        UI.sys("----- WINNER IDENTITY -----")
        inspect_certificate(winner_cert_pem)
        UI.sys("---------------------------")
        
        # Cleanup: The deal is concluded, remove the key to prevent replay or leakage
        remove_winning_key(client_state.auctions, auction_id)
        UI.end_step("Auction Process", "COMPLETED")

    except Exception as e:
        UI.error(f"[SECURITY] GCM Decryption Failure (Private Content): {e}")
        return    

def send_winner_identity(client_state, auction_id, deal_key):
    """
    Encrypts and broadcasts the winner's identity (certificate) to the auction owner.
    
    This is triggered after the winner has successfully verified the auction owner's identity.

    Args:
        client_state: The main client state object.
        auction_id (str): The unique identifier of the auction.
        deal_key (bytes): The symmetric key shared between winner and owner.
    """
    
    # Prepare the payload containing the winner's certificate
    private_payload_obj = {
        "certificate": b64e(client_state.cert_pem)
    }

    # Encrypt the inner payload with the specific DEAL KEY (Point-to-Point security logic)
    private_payload_json = json.dumps(private_payload_obj)
    private_payload = encrypt_message_symmetric_gcm(private_payload_json, deal_key)

    try:
        token_data = client_state.token_manager.get_token()
    except Exception as e:
        UI.error(f"Auction could not be created: {e}")
        return None

    timestamp = get_valid_timestamp()

    # Construct the network message
    msg = {
        "type": "winner_revelation",
        "auction_id": auction_id,
        "token": token_data,       # Proof of participation rights
        "private_info": private_payload, # Encrypted identity
        "timestamp": timestamp
    }

    response_json = json.dumps(msg)
    
    # Encrypt the outer message with the GROUP KEY (Network transport security)
    c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

    from network.tcp import send_to_peers
    send_to_peers(c_response_json, client_state.peer.connections)    


def prepare_winner_identity(client_state, msg):
    """
    Step 1 of Identity Exchange: The Winner receives the Auction Owner's revelation.
    
    The winner verifies the Owner's blinding factors (proving they created the auction token)
    and validates their certificate. If valid, the winner triggers 'send_winner_identity'.

    Args:
        client_state: The main client state object.
        msg (dict): The message containing the owner's revealed data.
    """
    
    auction_id = msg.get("auction_id")
    
    # Check if we hold the winning key for this auction
    deal_key = get_winning_key(client_state.auctions, auction_id)

    if deal_key == None:
        UI.warn(f"Ignored owner revelation for auction {auction_id} (Not a winner).")
        return
    
    UI.step("Verifying Auction Owner", "PROCESSING")
    
    private_payload_crypted_json = msg.get("private_info")
    
    try:
        # Decrypt the owner's private info using the Deal Key
        private_payload_json = decrypt_message_symmetric_gcm(
            private_payload_crypted_json, 
            deal_key
        )
        
        # Expected Data:
        # "token_auction_id": The original ID of the auction token
        # "blinding_factor_r": The secret 'r' used to blind the token (Linkability proof)
        # "certificate": The Owner's X.509 certificate

        private_info_obj = json.loads(private_payload_json)

        revealed_token_id = private_info_obj.get("token_auction_id")
        r_reveald = private_info_obj.get("blinding_factor_r")
        auctioner_cert_pem = b64d(private_info_obj.get("certificate"))
        
        UI.success("Owner Announcement Decrypted")
        UI.sub_info(f"Auction Token ID: {revealed_token_id}")
        UI.sub_info(f"Blinding Factor 'r': {format_large_int(r_reveald)}")

        # --- CRYPTOGRAPHIC VERIFICATION ---
        # 1. Find the signature associated with this token ID in the local ledger
        token_sig = client_state.ledger.find_token_signature(revealed_token_id)
        
        # 2. Verify that the provided blinding factor 'r' correctly unblinds to the token signature
        # This proves the sender is the legitimate owner who requested the token from the CA.
        if not verify_peer_blinding_data(client_state.ca_pub_pem, client_state.uuid, revealed_token_id, r_reveald, token_sig):
            UI.sub_error("Owner verification failed.")
            return

        # 3. Inspect and display the Owner's Certificate
        UI.sys("----- AUCTION OWNER IDENTITY -----")
        inspect_certificate(auctioner_cert_pem)
        UI.sys("----------------------------------")

    except Exception as e:
        UI.sub_security(f"GCM Decryption Failure (Private Content): {e}")
        return
    
    # If