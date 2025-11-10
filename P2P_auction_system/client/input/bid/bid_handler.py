import json
from client.ledger.ledger_handler import load_ledger, save_ledger

def cmd_bid():
    ledger = load_ledger()

    # Filter auctions NOT owned by this user
    auctions = [entry for entry in ledger if "id" in entry and entry.get("owner") != "me" and entry.get("type") == "auction"]

    if not auctions:
        print("No available auctions (not yours).")
        return

    print("\nAvailable auctions:")
    for a in auctions:
        print(f"ID {a['id']} | {a['name']} | min bid: {a['min_bid']}")

    # Make sure auction exists
    auction = None
    while True:
        try:
            target = int(input("\nSelect auction ID: ").strip())
        except ValueError:
            print("Invalid number.")
            continue    

        auction = next((x for x in auctions if x.get("id") == target), None)
        if auction:
            break
        else:
            print("Auction not found or not allowed. Try again.")


    # Enter bid amount
    while True:
        try:
            bid = float(input("Bid amount: ").strip())
        except ValueError:
            print("Invalid number.")
            continue

        if bid < auction["min_bid"]:
            print(f"Bid must be >= {auction['min_bid']}")
            continue

        break

    # Generate progressive bid ID
    bid_id = max(item.get("id", 0) for item in ledger) + 1

    # Full bid stored locally
    bid_obj_local = {
        "id": bid_id,
        "type": "bid",
        "auction_id": target,
        "bid": bid,
        "bidder": "me"
    }

    # JSON safe for network
    bid_obj_public = {
        "id": bid_id,
        "type": "bid",
        "auction_id": target,
        "bid": bid
    }

    ledger.append(bid_obj_local)
    save_ledger(ledger)

    print()
    print(f"Bid created with ID {bid_id}")

    bid_json = json.dumps(bid_obj_public)

    print("JSON ready to broadcast:")
    print(bid_json)
    print()

    ##############################################################
    # TODO: broadcast bid_json to all users                      #
    ##############################################################

    return bid_json
