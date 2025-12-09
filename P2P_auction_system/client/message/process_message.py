import json
import time
from crypto.keys.group_keys import find_my_new_key
from client.ca_handler.ca_message import verify_timestamp_signature
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm
from client.message.auction.auction_end_handler import handle_auction_end
from client.message.winner_reveal.winner_reveal_handler import handle_winner_reveal
from client.message.auction.auction_handler import update_auction_higher_bid, add_auction
from client.message.winner_reveal.final_revelation import prepare_winner_identity, get_client_identity
from client.ledger.ledger_handler import ledger_request_handler, ledger_update_handler
from design.ui import UI 

def is_auction_closed(auctions, auction_id):
    now = int(time.time())
    
    auction_data = auctions["auction_list"].get(auction_id)
    
    if not auction_data:
        return True

    closing_time = auction_data.get("closing_date")

    if closing_time is None:
        return False
        
    return now >= closing_time

def verify_double_spending(token_id, client):
    return client.ledger.token_used(token_id)

def update_personal_auctions(client, msg):
    token_data = msg.get("token_data")
    if msg.get("type") == "auction":
        auction_id = msg.get("id")
        min_bid = msg.get("min_bid")
        closing_date = msg.get("closing_date")
        public_key = msg.get("public_key")
        
        add_auction(client.auctions, auction_id, min_bid, closing_date, "False", token_data, public_key)

    else:
        auction_id = msg.get("auction_id")
        new_bid = msg.get("bid")

        update_auction_higher_bid(client.auctions, auction_id, new_bid, "False", token_data)


def process_message(msg, client_state):

    message_types = ["auction",
                     "bid", 
                     "ledger_request",
                     "ledger_update", 
                     "auctionEnd", 
                     "winner_token_reveal",
                     "auction_owner_revelation",
                     "winner_revelation"]

    try:
        obj = json.loads(msg)
    except:
        UI.error("Received non-JSON message; ignored")
        return


    mtype = obj.get("type")

    UI.peer(f"Received new {mtype}")

    if mtype in message_types:

        # === 1. VERIFICAÇÃO DE TOKENS ===
        token_data = obj.get("token")
        if not token_data:
            UI.sub_error("Rejected: Missing Token Data")
            return

        token_id = token_data.get("token_id")
        token_sig = token_data.get("token_sig")

        if not client_state.token_manager.verify_token(token_id, token_sig):
            UI.sub_security(f"Invalid Token Signature (Msg ID: {obj.get('id')})")
            return

        if verify_double_spending(token_id, client_state):
            UI.sub_security(f"Double Spending Attempt Detected (Token {token_id})")
            return

        # === 2. TIMESTAMP VERIFICATION ===
        timestamp_data = obj.get("timestamp")

        if not timestamp_data:
            UI.sub_security(f"Rejected {mtype}: Missing Timestamp")
            return

        # Verifie CA Signature
        if not verify_timestamp_signature(client_state.ca_pub_pem, timestamp_data):
            UI.sub_security(f"Invalid CA Signature on Timestamp (Msg ID: {obj.get('id')})")
            return

        # == Auction Logic Messages
        if mtype in ("auction", "bid"):

            should_process = True

            if mtype == "bid":
                if is_auction_closed(client_state.auctions, obj.get('auction_id')):
                    current_sync_time = int(time.time() + client_state.time_offset)
                    UI.sub_auction(f"Bid Rejected: Auction Expired ({current_sync_time})")
                    should_process = False

            if should_process:
                if client_state.ledger.add_action(obj) == 1:
                    client_state.ledger.save_to_file(client_state.user_path / "ledger.json")
                update_personal_auctions(client_state, obj)
                
                UI.sub_auction(f"New {mtype} stored in Ledger (ID: {obj.get('id')})")

        # == End of Auction Related Messages
        elif mtype == "auctionEnd":
            handle_auction_end(client_state, obj)
            if client_state.ledger.add_action(obj) == 1:
                client_state.ledger.save_to_file(client_state.user_path / "ledger.json")

        elif mtype == "winner_token_reveal":
            handle_winner_reveal(client_state, obj)

        elif mtype == "auction_owner_revelation":
            prepare_winner_identity(client_state, obj)

        elif mtype == "winner_revelation":
            get_client_identity(client_state, obj)

        # == Ledger Related Messages
        elif mtype == "ledger_request":
            from network.tcp import send_to_peers
            update_json = ledger_request_handler(obj.get("request_id"), client_state)

            if update_json:
                c_update_json = encrypt_message_symmetric_gcm(update_json, client_state.group_key)
                send_to_peers(c_update_json, client_state.peer.connections)

        elif mtype == "ledger_update":
            if not client_state.ledger_request_id == 0:
                UI.sub_peer("Ledger Synchronized Successfully")
                ledger_update_handler(client_state, obj)

    # == New key from CA
    elif mtype == "new_key":

        keys = obj.get("encrypted_keys")
        new_group_key = find_my_new_key(keys, client_state.private_key)

        if not new_group_key == None:
            client_state.group_key = new_group_key
            UI.sub_security("Group Key Rotated Successfully")

    else:
        UI.sub_error(f"Unknown message type received: {mtype}")