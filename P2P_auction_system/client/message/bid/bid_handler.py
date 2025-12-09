import secrets
import json, random
from design.ui import UI
from crypto.encoding.b64 import b64e
from crypto.crypt_decrypt.hybrid import hybrid_encrypt
from client.ca_handler.ca_message import get_valid_timestamp
from client.message.auction.auction_handler import get_auction_higher_bid, check_auction_existence, update_auction_higher_bid


def cmd_bid(auction_id, bid, client):
    
    UI.step("Processing Bid Request", "START")

    # Make sure auction exists
    try:
        auction_id = int(auction_id)
    except ValueError:
        UI.setup_error("Invalid auction ID format.")
        return None    

    try:
        bid = float(bid)
    except ValueError:
        UI.setup_error("Invalid bid amount format.")
        return None 
    

    if not check_auction_existence(client.auctions, auction_id):
        UI.sub_error(f"The auction {auction_id} doesn't exist!")
        return

    current_high = get_auction_higher_bid(client.auctions, auction_id)
    if bid < current_high:
        UI.sub_warn(f"Bid too low! Current highest is {current_high}.")
        return

    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        UI.sub_error(f"Unable to retrieve token: {e}")
        return None

    bid_id = random.randint(0, 1000000000)

    identity_pkg = {
        "real_uid": client.uuid,
        "cert_pem_b64": b64e(client.cert_pem) if isinstance(client.cert_pem, bytes) else client.cert_pem,
        "token_id_bound": token_data["token_id"],
        "nonce": secrets.token_hex(16)
    }

    encrypted_identity_blob = hybrid_encrypt(identity_pkg, client.ca_pub_pem)

    timestamp = get_valid_timestamp()

    bid_obj = {
        "id": bid_id,
        "type": "bid",
        "auction_id": auction_id,
        "bid": bid,
        "token": token_data,
        "encrypted_identity": encrypted_identity_blob,
        "timestamp": timestamp
    }

    
    from client.message.process_message import is_auction_closed
    if is_auction_closed(client.auctions, auction_id):
        UI.sub_error(f"Offer rejected. Time expired.")
        return None
    else:
        update_auction_higher_bid(client.auctions, auction_id, bid, "True", token_data)    

    UI.end_step(f"Bid {bid_id} created", "SUCCESS")

    bid_json = json.dumps(bid_obj)

    return bid_json