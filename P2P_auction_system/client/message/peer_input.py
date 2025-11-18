from client.message.auction.auction_handler import cmd_auction
from client.message.bid.bid_handler import cmd_bid
from client.ledger.ledger_handler import load_public_ledger, load_local_ledger

def print_auctions(config):
    public_ledger = load_public_ledger(config)
    local_ledger = load_local_ledger(config)

    # Crear lista de IDs de auctions propias
    my_auction_ids = [entry["id"] for entry in local_ledger if entry.get("type") == "auction"]

    # Filtrar auctions públicas que NO son nuestras
    auctions = [
        entry for entry in public_ledger
        if entry.get("type") == "auction" and entry.get("id") not in my_auction_ids
    ]

    if not auctions:
        print("No available auctions (not yours).")
        return

    print("\nAvailable auctions:")
    for a in auctions:
        print(f"ID {a['id']} | {a['name']} | min bid: {a['min_bid']}")

def menu_user(config):

    print_auctions(config)

    print("\nAvailable commands:")
    print(" /bid {auction_id} {min_bid}")
    print(" /auction {name} {min_bid}")
    # print(" /status")
    print(" /exit\n")

def peer_input(config, client_state):

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

        msg = cmd_bid(config, auction_id, min_bid, client_state.token_manager)

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

        msg = cmd_auction(config, auction_name, min_bid, client_state.token_manager)
    # elif user_input == "status":
    #     msg = cmd_status()
    #     msg = "nothing"
    elif user_input == "exit":
        msg = "exit"
    elif user_input == "help":
        menu_user()
    else:
        print("Unknown command.")

    return msg

