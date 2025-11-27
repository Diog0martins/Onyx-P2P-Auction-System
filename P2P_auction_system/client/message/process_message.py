import json
from client.ledger.ledger_handler import load_public_ledger, ledger_request_handler, ledger_update_handler

from client.message.auction.auction_handler import update_auction_higher_bid, add_auction


def verify_double_spending(token_id, config):
    ledger = load_public_ledger(config)
    for entry in ledger:
        # Verifica se a entrada tem token e se o ID é igual
        if "token" in entry:
            existing_id = entry["token"].get("token_id")
            if existing_id == token_id:
                return True # Já foi gasto!
    return False


def update_personal_auctions(client, msg):

    if msg.get("type") == "auction":

        auction_id = msg.get("id")
        min_bid = msg.get("min_bid")
        add_auction(client.auctions, auction_id, min_bid)

    else:
        auction_id = msg.get("auction_id")
        new_bid = msg.get("bid")

        update_auction_higher_bid(client.auctions, auction_id, new_bid, "False")



def process_message(msg, client_state):
    try:
        obj = json.loads(msg)
    except:
        print("[!] Received non-JSON message; ignored")
        print("RAW MESSAGE:", repr(msg))
        return

    mtype = obj.get("type")

    if mtype in ("auction", "bid", "ledger_request", "ledger_update"):
        token_data = obj.get("token")
        if not token_data:
            print(f"[!] Mensagem {mtype} rejeitada: Sem token.")
            return

        token_id = token_data.get("token_id")
        token_sig = token_data.get("token_sig")

        if not client_state.token_manager.verify_token(token_id, token_sig):
            print(f"[Security] ALERTA: Assinatura do Token inválida na mensagem {obj.get('id')}. Ignorada.")
            return

        """ CORRECT LATER! NO LONGER USING TWO LEDGERS !!!!!!!!! (Diogo)      
        if verify_double_spending(token_id, config):
            print(f"[Security] ALERTA: Tentativa de Double Spending (Token {token_id}). Ignorada.")
            return
        """
        if mtype in ("auction", "bid"):
            if client_state.ledger.add_action(obj) == 1:
                client_state.ledger.save_to_file(client_state.user_path / "ledger.json") 


            update_personal_auctions(client_state, obj)
            print(f"[✓] Stored {mtype} (id={obj.get('id')}) in ledger")

        elif mtype == "ledger_request":
            from network.tcp import send_to_peers
            print("Received request for ledger!")
            update_json = ledger_request_handler(obj.get("request_id"), client_state)
            send_to_peers(update_json, client_state.peer.connections)
        
        elif mtype == "ledger_update":
            if not client_state.ledger_request_id == 0:
                print("Receive updated ledger!")
                ledger_update_handler(client_state, obj)

    else:
        print(f"[?] Unknown message type received: {mtype}")