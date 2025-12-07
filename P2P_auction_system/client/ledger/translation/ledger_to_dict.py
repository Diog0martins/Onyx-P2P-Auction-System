import json

def parse_event(event):
    if event is None:
        return None
    if isinstance(event, dict):
        return event
    if isinstance(event, str):
        event = event.strip()
        if event == "":
            return None
        try:
            return json.loads(event)
        except json.JSONDecodeError:
            return None
    return None

# -------------------------------
#   EVENT HANDLERS
# -------------------------------

def _ensure_auction_entry(auctions, auction_id):
    """
    Creates a default auction entry if it doesn't exist.
    Returns the key (int) or None if invalid.
    """
    try:
        key = int(auction_id)
    except (TypeError, ValueError):
        return None

    if key not in auctions["auction_list"] or not isinstance(auctions["auction_list"][key], dict):
        auctions["auction_list"][key] = {
            "highest_bid": 0.0,
            "my_bid": "False",
            "closing_date": 0,
            "auction_token_data": "None",
            "finished": False,
            "public_key": "None",
            "last_bid_token_data": "None"
        }
    return key

def handle_auction_open(auctions, event, token_manager):
    auction_id = event.get("id")
    min_bid = event.get("min_bid", 0.0)
    pub_key = event.get("public_key")
    closing_date = event.get("closing_date")
    token_data = event.get("token") 

    if auction_id is None:
        return

    key = _ensure_auction_entry(auctions, auction_id)
    if key is None:
        return

    # 1. Update General Auction List Info
    entry = auctions["auction_list"][key]
    entry["highest_bid"] = max(entry["highest_bid"], float(min_bid))
    
    if pub_key:
        entry["public_key"] = pub_key
    
    if closing_date:
        entry["closing_date"] = int(closing_date)

    # 2. Handle Token Data & Ownership
    if token_data and isinstance(token_data, dict):
        entry["auction_token_data"] = token_data
        
        # --- STRICT OWNERSHIP CHECK ---
        t_id = token_data.get("token_id")
        
        if t_id and token_manager and token_manager.is_token_owner(t_id):
            # We initialize my_auctions with the current highest bid (which is min_bid at start)
            auctions["my_auctions"][str(key)] = {
                "public_key": pub_key,
                "auction_token_data": token_data,
                "highest_bid": entry["highest_bid"], # <--- Added this to ensure init value is not N/A
                "finished": entry["finished"]
            }

    # Update global counter
    try:
        auctions["last_auction_id"] = max(int(auctions.get("last_auction_id", 0)), key)
    except (TypeError, ValueError):
        pass

def handle_bid_event(auctions, event, token_manager):
    auction_id = event.get("auction_id")
    bid_amount = event.get("bid")
    token_data = event.get("token") 

    if auction_id is None or bid_amount is None:
        return

    key = _ensure_auction_entry(auctions, auction_id)
    if key is None:
        return

    try:
        bid_val = float(bid_amount)
    except (TypeError, ValueError):
        return

    entry = auctions["auction_list"][key]
    current_high = entry.get("highest_bid", 0.0)

    # Only process if this bid is the new highest
    if bid_val > current_high:
        # 1. Update the main auction list
        entry["highest_bid"] = bid_val
        entry["last_bid_token_data"] = token_data if token_data else "None"

        # 2. Check if this bid belongs to me
        is_mine = False
        if token_data and isinstance(token_data, dict) and token_manager:
            t_id = token_data.get("token_id")
            if t_id and token_manager.is_token_owner(t_id):
                is_mine = True
        entry["my_bid"] = "True" if is_mine else "False"

        # 3. SYNC WITH MY_AUCTIONS (Fix for "N/A" issue)
        # If I am the owner of this auction, I need to see the highest bid in 'my_auctions' too.
        str_key = str(key)
        if str_key in auctions["my_auctions"]:
            auctions["my_auctions"][str_key]["highest_bid"] = bid_val
            # Optionally update the last bid token data in my_auctions if your UI needs it
            if token_data:
                 auctions["my_auctions"][str_key]["last_bid_token_data"] = token_data

def handle_auction_end(auctions, event):
    auction_id = event.get("auction_id")
    if auction_id is None:
        return

    try:
        key = int(auction_id)
    except (TypeError, ValueError):
        return

    if key in auctions["auction_list"]:
        # Mark as finished in main list
        auctions["auction_list"][key]["finished"] = True
        
        # If it is in 'my_auctions', mark it finished there too
        if str(key) in auctions["my_auctions"]:
            auctions["my_auctions"][str(key)]["finished"] = True

        # If I am the highest bidder ("my_bid": "True"), I won.
        if auctions["auction_list"][key]["my_bid"] == "True":
            auctions["winning_auction"][str(key)] = auctions["auction_list"][key]

# -------------------------------
#   MAIN FUNCTION
# -------------------------------

def ledger_to_auction_dict(ledger, token_manager):
    auctions = {
        "last_auction_id": 0,
        "auction_list": {},
        "my_auctions": {},
        "winning_auction": {},
    }

    # Access the chain safely
    chain = getattr(ledger, "chain", []) or []

    for block in chain:
        events = block.get("events", [])
        for raw_event in events:
            event = parse_event(raw_event)
            if not event:
                continue

            event_type = event.get("type")

            if event_type == "auction":
                handle_auction_open(auctions, event, token_manager)
            
            elif event_type == "bid":
                handle_bid_event(auctions, event, token_manager)
            
            elif event_type == "auctionEnd":
                handle_auction_end(auctions, event)

    # Ensure last_auction_id is consistent
    try:
        keys = [int(k) for k in auctions["auction_list"].keys() if str(k).isdigit()]
        if keys:
            curr = int(auctions.get("last_auction_id", 0))
            auctions["last_auction_id"] = max(curr, max(keys))
    except Exception:
        pass

    return auctions