import json
import secrets
from design.ui import UI
from crypto.encoding.b64 import b64e
from datetime import datetime, timedelta, timezone 
from crypto.keys.keys_crypto import generate_key_pair
from crypto.crypt_decrypt.hybrid import hybrid_encrypt
from client.ca_handler.ca_message import get_valid_timestamp

AUCTION_DURATION_SECONDS = 30

def cmd_auction(client, name, bid):
    
    UI.step("Creating New Auction", "START")
    
    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        UI.sub_error(f"Unable to obtain token: {e}")
        return None

    auction_id = generate_next_auction_id(client.auctions)
    
    UI.sub_step("ID Generated", auction_id)
    
    private_key_pem, public_key_pem = generate_key_pair()

    private_key_str = private_key_pem.decode("utf-8")
    public_key_str = public_key_pem.decode("utf-8")

    future_time = datetime.now(timezone.utc) + timedelta(seconds=AUCTION_DURATION_SECONDS)
    closing_timestamp = int(future_time.timestamp())

    identity_pkg = {
        "real_uid": client.uuid,
        "cert_pem_b64": b64e(client.cert_pem) if isinstance(client.cert_pem, bytes) else client.cert_pem,
        "token_id_bound": token_data["token_id"],
        "nonce": secrets.token_hex(16)
    }

    encrypted_identity_blob = hybrid_encrypt(identity_pkg, client.ca_pub_pem)
    timestamp = get_valid_timestamp()

    # Broadcast version
    auction_obj = {
        "id": auction_id,
        "type": "auction",
        "name": name,
        "closing_date": closing_timestamp,
        "min_bid": bid,
        "token": token_data,
        "public_key": public_key_str,
        "encrypted_identity": encrypted_identity_blob,
        "timestamp": timestamp,
    }

    add_my_auction(client.auctions, auction_id, public_key_str, private_key_str, bid, closing_timestamp, token_data, public_key_str)

    UI.end_step(f"Auction {auction_id} ({name})", "CREATED")

    # JSON ready to send
    auction_json = json.dumps(auction_obj)

    return auction_json


# ----- Utilities to have in run auction data -----

def add_auction(auctions, auction_id, highest_bid, closing_timestamp, mine, used_token, public_key):
    if auction_id in auctions["auction_list"]:
        return False

    if auctions["last_auction_id"] < auction_id:
        auctions["last_auction_id"] = auction_id

    auctions["auction_list"][auction_id] = {
        "highest_bid": highest_bid,
        "my_bid": mine,
        "closing_date": closing_timestamp,
        "auction_token_data": used_token,
        "finished": False,
        "public_key": public_key
    }

    return True

def get_auction_higher_bid(auctions: dict, auction_id: int):
    auction = auctions["auction_list"].get(auction_id)
    return auction["highest_bid"] if auction else None

def update_auction_higher_bid(auctions, auction_id, new_bid, is_my_bid, used_token):
    if auction_id not in auctions["auction_list"]:
        return False

    auctions["auction_list"][auction_id]["highest_bid"] = new_bid
    auctions["auction_list"][auction_id]["my_bid"] = is_my_bid
    auctions["auction_list"][auction_id]["last_bid_token_data"] = used_token
    
    return True

def add_my_auction(auctions, auction_id, public_key, private_key, starting_bid, closing_timestamp, used_token, public_key_str):
    added = add_auction(auctions, auction_id, starting_bid, closing_timestamp, "True", used_token, public_key_str)
    if not added:
        return False

    auctions["my_auctions"][auction_id] = {
        "public_key": public_key,
        "private_key": private_key,
        "auction_token_data": used_token,
        "finished": False
    }

    return True

def generate_next_auction_id(auctions):
    next_id = int(auctions["last_auction_id"]) + 1
    auctions["last_auction_id"] = next_id
    return next_id


def check_auction_existence(auctions, auction_id):
    return auction_id in auctions.get("auction_list", {})

def add_winning_key(auctions_data, auction_id, crypto_key):
    auctions_data["winning_auction"][auction_id] = crypto_key

def remove_winning_key(auctions_data, auction_id):
    auctions_data["winning_auction"].pop(auction_id, None)

def get_winning_key(auctions_data, auction_id):
    return auctions_data["winning_auction"].get(auction_id)