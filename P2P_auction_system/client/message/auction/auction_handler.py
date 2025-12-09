import json
import secrets
from design.ui import UI
from crypto.encoding.b64 import b64e
from datetime import datetime, timedelta, timezone 
from crypto.keys.keys_crypto import generate_key_pair
from crypto.crypt_decrypt.hybrid import hybrid_encrypt
from client.ca_handler.ca_message import get_valid_timestamp

AUCTION_DURATION_SECONDS = 20

# ============= Command Handler =============

def cmd_auction(client, name, bid):
    """
    Handles the creation of a new auction. It generates an ephemeral RSA key pair for the 
    auction (used later for the winner reveal phase), consumes a blind token to ensure 
    anonymity, and constructs the auction creation message with an encrypted identity package.
    """
    
    UI.step("Creating New Auction", "START")
    
    # 1. Obtain Anonymous Token
    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        UI.sub_error(f"Unable to obtain token: {e}")
        return None

    auction_id = generate_next_auction_id(client.auctions)
    UI.sub_step("ID Generated", auction_id)
    
    # 2. Generate Ephemeral Auction Keys (for future Winner Reveal)
    private_key_pem, public_key_pem = generate_key_pair()
    private_key_str = private_key_pem.decode("utf-8")
    public_key_str = public_key_pem.decode("utf-8")

    future_time = datetime.now(timezone.utc) + timedelta(seconds=AUCTION_DURATION_SECONDS)
    closing_timestamp = int(future_time.timestamp())

    # 3. Create Encrypted Identity Package (Accountability)
    identity_pkg = {
        "real_uid": client.uuid,
        "cert_pem_b64": b64e(client.cert_pem) if isinstance(client.cert_pem, bytes) else client.cert_pem,
        "token_id_bound": token_data["token_id"],
        "nonce": secrets.token_hex(16)
    }

    encrypted_identity_blob = hybrid_encrypt(identity_pkg, client.ca_pub_pem)
    timestamp = get_valid_timestamp()

    # 4. Construct Message
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

    # Update Local State
    add_my_auction(client.auctions, auction_id, public_key_str, private_key_str, bid, closing_timestamp, token_data, public_key_str)

    UI.end_step(f"Auction {auction_id} ({name})", "CREATED")

    return json.dumps(auction_obj)


# ============= Local State Utilities =============

def add_auction(auctions, auction_id, highest_bid, closing_timestamp, mine, used_token, public_key):
    """
    Adds a new auction discovered from the network to the local dictionary state.
    """
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
    """
    Retrieves the current highest bid amount for a specific auction.
    """
    auction = auctions["auction_list"].get(auction_id)
    return auction["highest_bid"] if auction else None

def get_auction_higher_bid_timestamp(auctions: dict, auction_id: int):
    """
    Retrieves the current highest bid amount for a specific auction.
    """
    auction = auctions["auction_list"].get(auction_id)

    try:
        if auction:
            timestamp = auction["timestamp"]
            return timestamp
    except:
        return None  

def update_auction_higher_bid(auctions, auction_id, new_bid, is_my_bid, used_token, timestamp):
    """
    Updates the local state of an auction with a new valid highest bid.
    """
    if auction_id not in auctions["auction_list"]:
        return False

    auctions["auction_list"][auction_id]["highest_bid"] = new_bid
    auctions["auction_list"][auction_id]["my_bid"] = is_my_bid
    auctions["auction_list"][auction_id]["last_bid_token_data"] = used_token
    auctions["auction_list"][auction_id]["timestamp"] = timestamp

    return True


def add_my_auction(auctions, auction_id, public_key, private_key, starting_bid, closing_timestamp, used_token, public_key_str):
    """
    Registers an auction created by the local user, storing the private key required 
    to decrypt the winner's identity later.
    """
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
    """
    Calculates the next available auction ID based on the highest known ID in the ledger.
    """
    next_id = int(auctions["last_auction_id"]) + 1
    auctions["last_auction_id"] = next_id
    return next_id


def check_auction_existence(auctions, auction_id):
    """
    Verifies if a specific auction ID exists in the local state.
    """
    return auction_id in auctions.get("auction_list", {})


def add_winning_key(auctions_data, auction_id, crypto_key):
    """
    Stores the symmetric 'deal_key' used during the winner reveal phase.
    """
    auctions_data["winning_auction"][auction_id] = crypto_key


def remove_winning_key(auctions_data, auction_id):
    """
    Removes the symmetric 'deal_key' after the reveal phase is complete.
    """
    auctions_data["winning_auction"].pop(auction_id, None)


def get_winning_key(auctions_data, auction_id):
    """
    Retrieves the stored symmetric 'deal_key' for a specific auction.
    """
    return auctions_data["winning_auction"].get(auction_id)