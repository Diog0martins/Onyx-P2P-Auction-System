import json
from client.ledger.ledger_handler import load_public_ledger, save_public_ledger, load_local_ledger, save_local_ledger

def cmd_bid(config, auction_id, min_bid, token_manager):
    public_ledger = load_public_ledger(config)
    local_ledger = load_local_ledger(config)

    # Crear lista de IDs de auctions propias
    my_auction_ids = [entry["id"] for entry in local_ledger if entry.get("type") == "auction"]

    # Filtrar auctions públicas que NÃO são nossas
    auctions = [
        entry for entry in public_ledger
        if entry.get("type") == "auction" and entry.get("id") not in my_auction_ids
    ]

    # if not auctions:
    #     print("No available auctions (not yours).")
    #     return

    # print("\nAvailable auctions:")
    # for a in auctions:
    #     print(f"ID {a['id']} | {a['name']} | min bid: {a['min_bid']}")


    # Make sure auction exists
    auction = None
    try:
        auction_id = int(auction_id)
    except ValueError:
        print("Invalid number.")
        return None    

    try:
        min_bid = float(min_bid)
    except ValueError:
        print("Invalid bid.")
        return None    

    auction = next((x for x in auctions if x.get("id") == auction_id), None)
    if auction is not None:
        if min_bid >= auction["min_bid"]:

            try:
                token_data = token_manager.get_token()
            except Exception as e:
                print(f"[!] Não foi possível licitar: {e}")
                return None

            # Generate progressive bid ID
            bid_id = max(item.get("id", 0) for item in public_ledger) + 1

            # JSON safe for network
            bid_obj = {
                "id": bid_id,
                "type": "bid",
                "auction_id": auction_id,
                "bid": min_bid,
                "token": token_data
            }

            public_ledger.append(bid_obj)
            local_ledger.append(bid_obj)
            save_public_ledger(public_ledger, config)
            save_local_ledger(local_ledger, config)

            print()
            print(f"Bid created with ID {bid_id}")

            bid_json = json.dumps(bid_obj)

            print("JSON ready to broadcast:")
            print(bid_json)
            print()

            return bid_json
        else:
            print("Invalid bid, bid >= min_bid.")
            return None
    else:
        print("No available auction, invalid id")
        return None


