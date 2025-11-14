import json
from client.ledger.ledger_handler import store_in_ledger


def process_message(msg, config):
    try:
        obj = json.loads(msg)
    except:
        print("[!] Received non-JSON message; ignored")
        return

    mtype = obj.get("type")

    if mtype in ("auction", "bid"):
        store_in_ledger(obj, config)
        print(f"[✓] Stored {mtype} (id={obj.get('id')}) in ledger")
    else:
        print(f"[?] Unknown message type received: {mtype}")