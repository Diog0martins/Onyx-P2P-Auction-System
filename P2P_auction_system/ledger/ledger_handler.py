import json, random
from pathlib import Path
from client.ledger.ledger_logic import Ledger, compare_chains

CONFIG_DIR = Path.cwd() / "config"

def load_public_ledger(config):
    ledger_file = CONFIG_DIR / config / "public_ledger.json"
    if ledger_file.exists():
        with ledger_file.open("r") as f:
            return json.load(f)
    return []

def ledger_request_handler(request_id, client):

    to_send = client.ledger.to_dict()

    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        print(f"[!] It was not possible to bid: {e}")
        return None

    upadte_obj = {
        "request_id": request_id,
        "type": "ledger_update",
        "ledger": to_send,
        "token": token_data
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

    upadte_obj = {
        "request_id": client.ledger_request_id,
        "type": "ledger_request",
        "token": token_data
    }

    upadte_json = json.dumps(upadte_obj)
    print(upadte_json)
    return upadte_json


def ledger_update_handler(client, ledger_update_message):   

    received_ledger = ledger_update_message.get("ledger")

    ledger = Ledger.from_dict(received_ledger)

    if compare_chains(client.ledger.chain, ledger.chain) == "remote":
        if ledger.verify_chain():
            client.ledger = ledger

            client.ledger.save_to_file(client.user_path / "ledger.json") 

            client.ledger_request_id = 0

def init_cli_ledger(client, user_path):
    ledger_path = user_path  / "ledger.json"
    
    if not ledger_path.exists():
        ledger_path.touch()

    current_ledger = Ledger.load_from_file(ledger_path)

    if current_ledger == None:
        print("No ledger existed!")
        client.ledger =  Ledger()
        client.ledger.save_to_file(ledger_path)
    else:
        print("Stored new ledger!")
        client.ledger = current_ledger

    return