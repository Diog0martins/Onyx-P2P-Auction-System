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

            status = "You are winning" if my_bid == "True" else "You are NOT winning"
            print(f"- Auction {auction_id}: highest bid = {highest} ({status})")

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

            print(f"- Auction {auction_id}: highest bid = {highest}")

    print("")
