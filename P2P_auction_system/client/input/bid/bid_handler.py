import json
from client.ledger.ledger_handler import load_public_ledger, save_public_ledger, load_local_ledger, save_local_ledger

def cmd_bid(config):
    public_ledger = load_public_ledger(config)
    local_ledger = load_local_ledger(config)

    # Crear lista de IDs de auctions propias
    my_auction_ids = [entry["id"] for entry in local_ledger if entry.get("type") == "auction"]

    # Filtrar auctions públicas que NO son nuestras
    auctions = [
        entry for entry in public_ledger
        if entry.get("type") == "auction" and entry.get("id") not in my_auction_ids
    ]

    if not auctions:
        print("No available auctions (not yours).")
        return

    print("\nAvailable auctions:")
    for a in auctions:
        print(f"ID {a['id']} | {a['name']} | min bid: {a['min_bid']}")

    # Make sure auction exists
    auction = None
    while True:
        user_input = input().strip()
        parts = user_input.split()
        # print(len(parts))

        try:
            auction_id = int(parts[0])
        except ValueError:
            print("Invalid number.")
            continue    

        try:
            min_bid = float(parts[1])
        except ValueError:
            print("Invalid bid.")
            continue    

        auction = next((x for x in auctions if x.get("id") == auction_id), None)
        if auction:
            if min_bid >= auction["min_bid"]:
                # Generate progressive bid ID
                bid_id = max(item.get("id", 0) for item in public_ledger) + 1

                # JSON safe for network
                bid_obj = {
                    "id": bid_id,
                    "type": "bid",
                    "auction_id": auction_id,
                    "bid": min_bid
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
            
    ##############################################################
    # TODO: broadcast bid_json to all users                      #
    ##############################################################


