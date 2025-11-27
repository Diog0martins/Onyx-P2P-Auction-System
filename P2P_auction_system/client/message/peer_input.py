from client.message.auction.auction_handler import cmd_auction
from client.message.bid.bid_handler import cmd_bid
import json


def menu_user():

    print("\nAvailable commands:")
    print(" /bid {auction_id} {min_bid}")
    print(" /auction {name} {min_bid}")
    print(" /status")
    print(" /exit\n")

def peer_input(client_state):

    user_input = input().strip()
    parts = user_input.split()

    if len(parts) == 0: return None
    command = parts[0]
    msg = None

    command = parts[0]

    if command == "bid":
        if len(parts) < 3:
            print("Usage: /bid <auction_id> <min_bid>")
            return None

        auction_id = parts[1]
        min_bid = parts[2]

        msg = cmd_bid(auction_id, min_bid, client_state)

    elif command == "auction":
        if len(parts) < 3:
            print("Usage: /auction <name> <min_bid>")
            return None

        auction_name = parts[1]
        try:
            min_bid = float(parts[2])
        except ValueError:
            print("Invalid number for min_bid")
            return None

        msg = cmd_auction(client_state, auction_name, min_bid)

    elif user_input == "exit":
        msg = "exit"

    elif user_input == "help":
        menu_user()

    elif user_input == "status":
        print(json.dumps(client_state.auctions, indent=4))

    else:
        print("Unknown command.")
        return None

    
    if client_state.ledger.add_action(msg) == 1:
        client_state.ledger.save_to_file(client_state.user_path / "ledger.json") 

    return msg

