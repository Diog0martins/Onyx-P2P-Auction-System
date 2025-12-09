import json
from design.ui import UI
from client.message.auction.auction_handler import cmd_auction
from client.message.bid.bid_handler import cmd_bid
from client.message.status_handler import print_auction_state


def menu_user():
    UI.help()

def peer_input(client_state):

    try:
        user_input = input("").strip()
    except EOFError:
        return "exit"

    parts = user_input.split()

    if len(parts) == 0: return None
    command = parts[0].lower()
    msg = None

    if command == "bid":
        if len(parts) < 3:
            UI.error("Usage: bid <auction_id> <min_bid>")
            return None

        auction_id = parts[1]
        min_bid = parts[2]

        msg = cmd_bid(auction_id, min_bid, client_state)

    elif command == "auction":
        if len(parts) < 3:
            UI.error("Usage: auction <name> <min_bid>")
            return None

        auction_name = parts[1]
        try:
            min_bid = float(parts[2])
        except ValueError:
            UI.error("Invalid number for min_bid")
            return None

        msg = cmd_auction(client_state, auction_name, min_bid)

    elif command == "exit":
        return "exit"

    elif command == "help":
        menu_user()
        UI.sys_ready()
        return None

    elif command == "status":
        print_auction_state(client_state.auctions)
        return None

    else:
        UI.warn("Unknown command.")
        return None

    if msg:
        ledger_action = json.loads(msg)
        if client_state.ledger.add_action(ledger_action) == 1:
            UI.sub_step("Ledger", "Action Saved")
            client_state.ledger.save_to_file(client_state.user_path / "ledger.json")


    return msg