import json, random

from client.message.auction.auction_handler import get_auction_higher_bid, check_auction_existence, update_auction_higher_bid

def cmd_bid(auction_id, bid, client):

    # Make sure auction exists
    auction = None
    try:
        auction_id = int(auction_id)
    except ValueError:
        print("Invalid id.")
        return None    

    try:
        bid = float(bid)
    except ValueError:
        print("Invalid bid.")
        return None 
    

    if not check_auction_existence(client.auctions, auction_id):
        print(f"The auction {auction_id} doesn't exist!")
        return

    if bid < get_auction_higher_bid(client.auctions, auction_id):
        print(f"Someone did a higher bid of {get_auction_higher_bid(client.auctions, auction_id)}!")
        return

    try:
        token_data = client.token_manager.get_token()
    except Exception as e:
        print(f"[!] It was not possible to bid: {e}")
        return None

    # MAYBE DELETE LATER! ====================================================
    bid_id = random.randint(0, 1000000000) 


    # JSON safe for network
    bid_obj = {
        "id": bid_id,
        "type": "bid",
        "auction_id": auction_id,
        "bid": bid,
        "token": token_data
    }

    update_auction_higher_bid(client.auctions, auction_id, bid, "True")    

    print()
    print(f"Bid created with ID {bid_id}")

    bid_json = json.dumps(bid_obj)

    print("JSON ready to broadcast:")
    print(bid_json)
    print()

    return bid_json



