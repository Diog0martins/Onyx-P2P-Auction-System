import json
from client.ledger.ledger_handler import load_ledger, save_ledger


def cmd_auction():
    # Ask for auction object
    auction_object = input("Auction object: ").strip()
    if not auction_object:
        print("Invalid name.")
        return

    # Ask for minimum bid
    try:
        min_bid = float(input("Minimum bid: ").strip())
    except ValueError:
        print("Invalid number.")
        return

    # Load existing ledger
    ledger = load_ledger()

    # Generate progressive auction_id
    if len(ledger) == 0:
        auction_id = 1
    else:
        # Get the LAST id among auctions
        auction_id = max(item.get("id", 0) for item in ledger) + 1

    # Full auction object stored privately
    auction_obj_local = {
        "id": auction_id,
        "type": "auction",
        "name": auction_object,
        "min_bid": min_bid,
        "owner": "me"       # <-- PRIVATE INFO
    }


    # Broadcast version (no owner)
    auction_obj_public = {
        "id": auction_id,
        "type": "auction",
        "name": auction_object,
        "min_bid": min_bid,
    }

    # Save locally
    ledger.append(auction_obj_local)
    save_ledger(ledger)

    print()
    print(f"Auction created with ID {auction_id}")

    # JSON ready to send
    auction_json = json.dumps(auction_obj_public)

    print("JSON ready to broadcast:")
    print(auction_json)
    print()

    ##########################################################
    # TODO: broadcast auction_json to other users            #
    ##########################################################

    return auction_json
