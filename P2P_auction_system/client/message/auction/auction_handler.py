import json

from crypto.keys.keys_crypto import generate_key_pair
from datetime import datetime, timedelta, timezone # Módulos de data/hora
import time # Para timestamp Unix

AUCTION_DURATION_SECONDS = 20

def cmd_auction(client, name, bid):
    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        print(f"[!] Não foi possível criar Auction: {e}")
        return None

    auction_id = generate_next_auction_id(client.auctions)
    private_key_pem, public_key_pem = generate_key_pair()

    private_key_str = private_key_pem.decode("utf-8")
    public_key_str = public_key_pem.decode("utf-8")

    future_time = datetime.now(timezone.utc) + timedelta(seconds=AUCTION_DURATION_SECONDS)
    closing_timestamp = int(future_time.timestamp())

    # Broadcast version
    auction_obj = {
        "id": auction_id,
        "type": "auction",
        "name": name,
        "closing_date": closing_timestamp,
        "min_bid": bid,
        "token": token_data,
        "public_key": public_key_str
    }

    add_my_auction(client.auctions, auction_id, public_key_str, private_key_str, bid, closing_timestamp, token_data, public_key_str)

    print()
    print(f"Auction created with ID {auction_id}")

    # JSON ready to send
    auction_json = json.dumps(auction_obj)

    print("JSON ready to broadcast:")
    print(auction_json)
    print()

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
    print(auctions)
    return auction_id in auctions.get("auction_list", {})

def add_winning_key(auctions_data, auction_id, crypto_key):
    auctions_data["winning_auction"][auction_id] = crypto_key

def remove_winning_key(auctions_data, auction_id):
    auctions_data["winning_auction"].pop(auction_id, None)

def get_winning_key(auctions_data, auction_id):
    return auctions_data["winning_auction"].get(auction_id)