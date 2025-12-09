import json, random
from client.ledger.ledger_logic import Ledger, compare_chains
from client.ledger.translation.ledger_to_dict import ledger_to_auction_dict
from client.ca_handler.ca_message import get_valid_timestamp


def ledger_request_handler(request_id, client):

    to_send = client.ledger.to_dict()

    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        print(f"[!] It was not possible to bid: {e}")
        return None

    timestamp = get_valid_timestamp()

    upadte_obj = {
        "request_id": request_id,
        "type": "ledger_update",
        "ledger": to_send,
        "token": token_data,
        "timestamp": timestamp
    }

    upadte_json = json.dumps(upadte_obj)

    return upadte_json


def prepare_ledger_request(client):

    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        print(f"[!] It was not possible to bid: {e}")
        return None

    client.ledger_request_id = random.randint(1, 1000000000)

    timestamp = get_valid_timestamp()

    update_obj = {
        "request_id": client.ledger_request_id,
        "type": "ledger_request",
        "token": token_data,
        "timestamp": timestamp
    }

    update_json = json.dumps(update_obj)
    return update_json


def ledger_update_handler(client, ledger_update_message):   

    received_ledger = ledger_update_message.get("ledger")

    ledger = Ledger.from_dict(received_ledger)

    if compare_chains(client.ledger.chain, ledger.chain) == "remote":
        if ledger.verify_chain():
            client.ledger = ledger

            client.ledger.save_to_file(client.user_path / "ledger.json") 

            client.ledger_request_id = 0

            translated_ledger = ledger_to_auction_dict(client.ledger, client.token_manager)

            client.auctions = translated_ledger


def init_cli_ledger(client, user_path):
    ledger_path = user_path  / "ledger.json"
    
    if not ledger_path.exists():
        ledger_path.touch()

    current_ledger = Ledger.load_from_file(ledger_path)

    if current_ledger == None:
        client.ledger =  Ledger()
        client.ledger.save_to_file(ledger_path)
    else:
        client.ledger = current_ledger

    return