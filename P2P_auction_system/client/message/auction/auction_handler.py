import json
from client.ledger.ledger_handler import load_public_ledger, save_public_ledger, load_local_ledger, save_local_ledger


def cmd_auction(config, name, bid):
    # Load existing ledger
    public_ledger = load_public_ledger(config)
    local_ledger = load_local_ledger(config)

    # Generate progressive auction_id
    if len(public_ledger) == 0:
        auction_id = 1
    else:
        # Get the LAST id among auctions
        auction_id = max(item.get("id", 0) for item in public_ledger) + 1

    # Broadcast version (no owner)
    auction_obj = {
        "id": auction_id,
        "type": "auction",
        "name": name,
        "min_bid": bid,
    }

    # Save locally
    public_ledger.append(auction_obj)
    local_ledger.append(auction_obj)
    save_public_ledger(public_ledger, config)
    save_local_ledger(local_ledger, config)

    print()
    print(f"Auction created with ID {auction_id}")

    # JSON ready to send
    auction_json = json.dumps(auction_obj)

    print("JSON ready to broadcast:")
    print(auction_json)
    print()

    ##########################################################
    # TODO: broadcast auction_json to other users            #
    ##########################################################

    return auction_json
