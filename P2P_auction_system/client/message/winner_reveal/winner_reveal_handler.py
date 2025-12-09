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
    """
    Constructs and sends a cryptographic proof that the current user is the valid owner/creator of the auction.
    
    This is the second half of the mutual revelation handshake. After verifying the winner,
    the owner reveals the blinding factor 'r' associated with the token used to CREATE the auction.
    
    Args:
        client_state: The main client state object.
        auction_id (str): The unique ID of the auction.
        deal_key (bytes): The symmetric session key established with the winner.
    """

    auction_list = client_state.auctions["auction_list"]
    info = auction_list.get(auction_id)

    # Get token used to create the auction originally
    auction_token = info.get("auction_token_data")
    
    # Prepare proof that token is owned by user
    if auction_token:

        token_id = auction_token.get("token_id")
        
        if token_id:
            # Retrieve the secret 'r' (blinding factor) from the local wallet.
            # Only the person who requested the token from the Bank knows this 'r'.
            r_value = client_state.token_manager.get_blinding_factor_r(token_id)

            if r_value is None:
                UI.error(f"Critical Error: Token ID {token_id} not found in local wallet.")
                return

            # Bundle the proof data: Token ID, Secret 'r', and the Owner's Certificate.
            private_payload_obj = {
                "token_auction_id": token_id,
                "blinding_factor_r": r_value,
                "certificate": b64e(client_state.cert_pem)
            }

            # Encrypt the proof using the Deal Key (Point-to-Point security)
            private_payload_json = json.dumps(private_payload_obj)
            private_payload = encrypt_message_symmetric_gcm(private_payload_json, deal_key)

            try:
                # Include a standard access token for network validation
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
            # Encrypt the outer message for the broadcast group
            c_response_json = encrypt_message_symmetric_gcm(response_json, client_state.group_key)

            UI.sub_step("Action", "Submitting blind factor 'r' disclosure")
            from network.tcp import send_to_peers
            send_to_peers(c_response_json, client_state.peer.connections)


def handle_winner_reveal(client_state, obj):
    """
    Processes the initial revelation from a potential winner.
    
    This function:
    1. Decrypts the session 'deal_key' using the Auction's RSA Private Key.
    2. Decrypts the winner's proof payload.
    3. Verifies the winner's token blinding factor against the ledger.
    4. If valid, triggers the Owner's counter-proof (send_auction_creation_proof).

    Args:
        client_state: The main client state object.
        obj (dict): The decrypted message payload received from the network.
    """

    auction_id = obj.get("auction_id")
    
    # Verify we are actually the owner of this auction
    my_auction = client_state.auctions["my_auctions"].get(auction_id)
    
    if my_auction is None:
        UI.error(f"Received WINNER_REVEAL for auction {auction_id} that does not belong to me.")
        return

    UI.step(f"Verifying Winner Claim (ID: {auction_id})", "PROCESSING")

    # Retrieve the Private Key generated specifically for this auction instance
    my_auction_private_key_pem = my_auction.get("private_key")
    
    if my_auction_private_key_pem is None:
        return

    cleaned_pem_string = my_auction_private_key_pem.strip()
    private_key_pem_bytes = cleaned_pem_string.encode('utf-8') 
    
    # Extract the encrypted symmetric key sent by the winner
    deal_key_encrypted_b64 = obj.get("deal_key")

    try:
        deal_key_encrypted_bytes = b64d(deal_key_encrypted_b64)
    except Exception as e:
        UI.sub_error(f"Failed to decode encrypted Deal Key Base64: {e}")
        return
    
    try:
        # Decrypt the AES session key using the Auction's RSA Private Key.
        # This ensures only the auction owner can read the subsequent proof data.
        deal_key_bytes = decrypt_with_private_key(
            deal_key_encrypted_bytes, 
            private_key_pem_bytes
        )
    except Exception as e:
        UI.sub_security(f"RSA Decryption Failure (Deal Key): {e}")
        return
    
    # Now decrypt the actual private proof data using the recovered AES key
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

        # --- VERIFICATION CRITICAL STEP ---
        # 1. Look up the blinded signature for this token ID in the public ledger.
        token_sig = client_state.ledger.find_token_signature(revealed_token_id)
        
        # 2. Mathematically verify that Unblind(Signature, r) matches the Token ID.
        # This confirms the winner possesses the original blinding factor and didn't just copy a token ID.
        if not verify_peer_blinding_data(client_state.ca_pub_pem, client_state.uuid, revealed_token_id, r_reveald, token_sig):
            UI.sub_error("Winner verification failed.")
            return
    
    except Exception as e:
        UI.sub_security(f"GCM Decryption Failure (Private Content): {e}")
        return
    
    # Store the verified session key for future communication
    add_winning_key(client_state.auctions, auction_id, deal_key_bytes)
    
    # Trigger the response: Send proof that WE are the auction owner
    send_auction_creation_proof(client_state, auction_id, deal_key_bytes)
    UI.end_step("Auction Owner Proof", "SENT")