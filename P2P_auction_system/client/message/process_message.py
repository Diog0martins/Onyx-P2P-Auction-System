import json
from client.ledger.ledger_handler import store_in_ledger, load_public_ledger

def verify_double_spending(token_id, config):
    ledger = load_public_ledger(config)
    for entry in ledger:
        # Verifica se a entrada tem token e se o ID é igual
        if "token" in entry:
            existing_id = entry["token"].get("token_id")
            if existing_id == token_id:
                return True # Já foi gasto!
    return False

def process_message(msg, config, client_state):
    try:
        obj = json.loads(msg)
    except:
        print("[!] Received non-JSON message; ignored")
        return

    mtype = obj.get("type")

    if mtype in ("auction", "bid"):
        token_data = obj.get("token")
        if not token_data:
            print(f"[!] Mensagem {mtype} rejeitada: Sem token.")
            return

        token_id = token_data.get("token_id")
        token_sig = token_data.get("token_sig")

        if not client_state.token_manager.verify_token(token_id, token_sig):
            print(f"[Security] ALERTA: Assinatura do Token inválida na mensagem {obj.get('id')}. Ignorada.")
            return

        if verify_double_spending(token_id, config):
            print(f"[Security] ALERTA: Tentativa de Double Spending (Token {token_id}). Ignorada.")
            return

        store_in_ledger(obj, config)
        print(f"[✓] Stored {mtype} (id={obj.get('id')}) in ledger")
    else:
        print(f"[?] Unknown message type received: {mtype}")