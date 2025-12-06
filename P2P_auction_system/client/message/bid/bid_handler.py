import json, random

from client.message.auction.auction_handler import get_auction_higher_bid, check_auction_existence, update_auction_higher_bid
from client.message.process_message import is_auction_closed
import time
import secrets

from client.message.auction.auction_handler import (
    get_auction_higher_bid,
    check_auction_existence,
    update_auction_higher_bid,
)

from crypto.encoding.b64 import b64e
from crypto.crypt_decrypt.hybrid import hybrid_encrypt

def cmd_bid(auction_id, bid, client):

    # Make sure auction exists
    auction = None
    try:
        auction_id = int(auction_id)
    except ValueError:
        print("Invalid id.")
        return None    

    try:
        bid = float(bid)
    except ValueError:
        print("Invalid bid.")
        return None 
    

    if not check_auction_existence(client.auctions, auction_id):
        print(f"The auction {auction_id} doesn't exist!")
        return

    if bid < get_auction_higher_bid(client.auctions, auction_id):
        print(f"Someone did a higher bid of {get_auction_higher_bid(client.auctions, auction_id)}!")
        return

    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        print(f"[!] It was not possible to bid: {e}")
        return None

    # MAYBE DELETE LATER! ====================================================
    bid_id = random.randint(0, 1000000000)

    identity_pkg = {
        "real_uid": client.uuid,
        "cert_pem_b64": b64e(client.cert_pem) if isinstance(client.cert_pem, bytes) else client.cert_pem,
        "token_id_bound": token_data["token_id"],
        "nonce": secrets.token_hex(16)
    }

    encrypted_identity_blob = hybrid_encrypt(identity_pkg, client.ca_pub_pem)

    bid_obj = {
        "id": bid_id,
        "type": "bid",
        "auction_id": auction_id,
        "bid": bid,
        "token": token_data,
        "encrypted_identity": encrypted_identity_blob
    }

    from client.message.process_message import is_auction_closed

    if is_auction_closed(client.auctions, auction_id):
        print(f"[X] Oferta rejeitada. Tempo expirado ({int(time.time())})")
    else:
        update_auction_higher_bid(client.auctions, auction_id, bid, "True", token_data)    

    print()
    print(f"Bid created with ID {bid_id}")

    bid_json = json.dumps(bid_obj)

    print("JSON ready to broadcast:")
    print(bid_json)
    print()

    return bid_json



