from datetime import datetime

def print_auction_state(state):
    auction_list = state.get("auction_list", {})
    my_auctions = state.get("my_auctions", {})

    print("\n=== Open Auctions ===")
    found_open = False
    for auction_id, info in auction_list.items():
        if not isinstance(info, dict):
            print(f"- Auction {auction_id}: INVALID ENTRY (skipped)")
            continue

        if auction_id not in my_auctions:
            found_open = True
            highest = info.get("highest_bid", 0)
            my_bid = info.get("my_bid", "False")
            timestamp = info.get("closing_date", 0)

            dt_object = datetime.fromtimestamp(timestamp) 

            formatted_time = dt_object.strftime("%d-%m-%Y %H:%M:%S")

            status = "You are winning" if my_bid == "True" else "You are NOT winning"
            print(f"- Auction {auction_id}: highest bid = {highest} ({status}), Closing Date: {formatted_time}")

    if not found_open:
        print("No open auctions available.")

    print("\n=== My Auctions ===")
    if not my_auctions:
        print("You have no auctions.")
    else:
        for auction_id in my_auctions:
            info = auction_list.get(auction_id, {})
            if isinstance(info, dict):
                highest = info.get("highest_bid", "N/A")
            else:
                highest = "INVALID"
            timestamp = info.get("closing_date", 0)

            dt_object = datetime.fromtimestamp(timestamp) 

            formatted_time = dt_object.strftime("%d-%m-%Y %H:%M:%S")

            print(f"- Auction {auction_id}: highest bid = {highest}, Closing Date: {formatted_time}")

    print("")
