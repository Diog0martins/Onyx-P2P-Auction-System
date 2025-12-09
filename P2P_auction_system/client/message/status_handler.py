from datetime import datetime

def print_auction_state(state):
    """
    Formats and prints the current status of all known auctions to the terminal.
    Separates auctions into 'General Network Auctions' and 'My Auctions', displaying 
    winning status, highest bids, and closing dates.
    """
    auction_list = state.get("auction_list", {})
    my_auctions = state.get("my_auctions", {})

    # Create a set of IDs that belong to "My Auctions" for easy filtering.
    my_auction_ids = set()
    for k in my_auctions.keys():
        try:
            my_auction_ids.add(int(k))
        except ValueError:
            pass

    # ==== Section 1: Other Peers' Auctions =====

    print("\n=== Auctions ===")
    found_general = False
    
    for auction_id, info in auction_list.items():
        if not isinstance(info, dict):
            continue

        # Filter: Skip my own auctions
        if auction_id in my_auction_ids:
            continue

        found_general = True
        
        highest = info.get("highest_bid", 0)
        my_bid_status = info.get("my_bid", "False") 
        timestamp = info.get("closing_date", 0)
        is_finished = info.get("finished", False)

        dt_object = datetime.fromtimestamp(timestamp) 
        formatted_time = dt_object.strftime("%d-%m-%Y %H:%M:%S")
        status = "You are winning" if my_bid_status == "True" else "You are NOT winning"
        
        prefix = "[Finished] " if is_finished else ""
        print(f"{prefix}- Auction {auction_id}: highest bid = {highest} ({status}), Closing Date: {formatted_time}")

    if not found_general:
        print("No general auctions available.")

    # ==== Section 2: My Auctions ====

    print("\n=== My Auctions ===")
    if not my_auctions:
        print("You have no auctions.")
    else:
        for auction_id in my_auctions:
            try:
                lookup_id = int(auction_id)
            except ValueError:
                lookup_id = auction_id
            
            # Get authoritative data from auction_list
            info = auction_list.get(lookup_id)
            
            # Fallback
            if not info:
                info = my_auctions[auction_id]

            if isinstance(info, dict):
                highest = info.get("highest_bid", "N/A")
                timestamp = info.get("closing_date", 0)
                is_finished = info.get("finished", False)
            else:
                highest = "INVALID"
                timestamp = 0
                is_finished = False

            dt_object = datetime.fromtimestamp(timestamp) 
            formatted_time = dt_object.strftime("%d-%m-%Y %H:%M:%S")

            prefix = "[Finished] " if is_finished else ""
            print(f"{prefix}- Auction {auction_id}: highest bid = {highest}, Closing Date: {formatted_time}")

    print("")