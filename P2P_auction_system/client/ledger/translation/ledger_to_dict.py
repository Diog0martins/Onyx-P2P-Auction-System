import json

def parse_event(event):
    """Normalize event into a Python dict.
    Events may arrive as:
    - None
    - dict
    - JSON-encoded string
    """
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

def handle_auction_open(auctions, event):
    """Process an auction creation event."""
    auction_id = event.get("id")
    min_bid = event.get("min_bid", 0)

    if auction_id is None:
        return

    auctions["auction_list"][auction_id] = min_bid

    # Update last_auction_id if needed
    if auction_id > auctions["last_auction_id"]:
        auctions["last_auction_id"] = auction_id


def handle_bid_event(auctions, event):
    """Process a bid event and update highest bid."""
    auction_id = event.get("auction_id")
    bid = event.get("bid")

    if auction_id is None or bid is None:
        return

    # Only update if auction exists
    if auction_id in auctions["auction_list"]:
        # Only update when higher
        if bid > auctions["auction_list"][auction_id]:
            auctions["auction_list"][auction_id] = bid


def handle_auction_end(auctions, event):
    """Process an auction_end event."""
    auction_id = event.get("auction_id")
    if auction_id in auctions["auction_list"]:
        del auctions["auction_list"][auction_id]


# -------------------------------  
#   MAIN TRANSLATION FUNCTION  
# -------------------------------  

def ledger_to_auction_dict(ledger):
    
    auctions = {
        "last_auction_id": 0,
        "auction_list": {},
        "my_auctions": {},
    }

    for block in ledger.chain:
        events = block.get("events", [])
        for raw_event in events:
            event = parse_event(raw_event)
            if not event:
                continue  # skip nulls

            event_type = event.get("type")

            if event_type == "auction":
                handle_auction_open(auctions, event)

            elif event_type == "bid":
                handle_bid_event(auctions, event)

            elif event_type == "auction_end":
                handle_auction_end(auctions, event)

    return auctions
