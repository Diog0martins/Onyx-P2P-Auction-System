from client.input.auction.auction_handler import cmd_auction
from client.input.bid.bid_handler import cmd_bid 

def menu_user():

    print("Available commands:")
    print(" /bid")
    print(" /auction")
    print(" /status")
    print(" /exit\n")

def peer_input():

    user_input = input().strip()

    if user_input == "bid":
        msg = cmd_bid()
    elif user_input == "auction":
        msg = cmd_auction()
    elif user_input == "status":
        #msg = cmd_status()
        msg = "nothing"
    elif user_input == "exit":
        msg = exit
    elif user_input == "help":
        menu_user()
    else:
        print("Unknown command.")

    return msg

