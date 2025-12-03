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
    """Ensure an auction entry exists in auction_list and return its key as int."""
    try:
        key = int(auction_id)
    except (TypeError, ValueError):
        return None

    if key not in auctions["auction_list"] or not isinstance(auctions["auction_list"][key], dict):
        auctions["auction_list"][key] = {
            "highest_bid": 0.0,
            "my_bid": False,
            "bid_id": 0, 
            "token": None
        }
    return key


def handle_auction_open(auctions, event):
    auction_id = event.get("id")
    min_bid = event.get("min_bid", 0.0)
    auction_public_key = event.get("public_key", None)

    if auction_id is None:
        return

    key = _ensure_auction_entry(auctions, auction_id)
    if key is None:
        return

    current = auctions["auction_list"][key].get("highest_bid", 0.0)

    auctions["auction_list"][key]["highest_bid"] = max(current, float(min_bid))

    if auction_public_key:
        auctions["auction_list"][key]["public_key"] = auction_public_key

    try:
        auctions["last_auction_id"] = max(int(auctions.get("last_auction_id", 0)), key)
    except (TypeError, ValueError):
        pass

def handle_bid_event(auctions, event):
    auction_id = event.get("auction_id")
    bid = event.get("bid")
    bid_id = int(event.get("id"))
    token = event.get("token")

    if auction_id is None or bid is None:
        return

    key = _ensure_auction_entry(auctions, auction_id)
    if key is None:
        return

    try:
        bid_val = float(bid)
    except (TypeError, ValueError):
        return

    current = auctions["auction_list"][key].get("highest_bid", 0.0)
    if bid_val > current:
        auctions["auction_list"][key]["highest_bid"] = bid_val
        auctions["auction_list"][key]["my_bid"] = False
        auctions["auction_list"][key]["bid_id"] = bid_id
        auctions["auction_list"][key]["token"] = token


def handle_auction_end(auctions, event):
    auction_id = event.get("auction_id")
    if auction_id is None:
        return

    try:
        key = int(auction_id)
    except (TypeError, ValueError):
        return

    if key in auctions["auction_list"]:
        del auctions["auction_list"][key]


# -------------------------------
#   MAIN TRANSLATION FUNCTION
# -------------------------------

def ledger_to_auction_dict(ledger):
    auctions = {
        "last_auction_id": 0,
        "auction_list": {},
        "my_auctions": {},
    }

    for block in getattr(ledger, "chain", []) or []:
        events = block.get("events", [])
        for raw_event in events:
            event = parse_event(raw_event)
            if not event:
                continue

            event_type = event.get("type")
            if event_type == "auction":
                handle_auction_open(auctions, event)
            elif event_type == "bid":
                handle_bid_event(auctions, event)
            elif event_type == "auction_end":
                handle_auction_end(auctions, event)

    try:
        keys = [int(k) for k in auctions["auction_list"].keys() if str(k).isdigit()]
        if keys:
            auctions["last_auction_id"] = max(auctions.get("last_auction_id", 0), max(keys))
    except Exception:
        pass

    return auctions