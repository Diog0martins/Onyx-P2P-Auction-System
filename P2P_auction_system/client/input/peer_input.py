from client.input.auction.auction_handler import cmd_auction
from client.input.bid.bid_handler import cmd_bid 

def menu_user():

    print("\nAvailable commands:")
    print(" /bid")
    print(" /auction {name} {min bid}")
    # print(" /status")
    print(" /exit\n")

def peer_input(config):

    user_input = input().strip()

    parts = user_input.split()

    if len(parts) == 0:
        return None

    command = parts[0]

    if user_input == "bid":
        msg = cmd_bid(config)
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

        msg = cmd_auction(config, auction_name, min_bid)
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

