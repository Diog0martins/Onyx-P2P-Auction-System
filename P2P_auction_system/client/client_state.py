class Client:
    def __init__(self, userID, user_path, public_key, private_key):
        self.userID = userID
        self.user_path = user_path
        self.public_key = public_key
        self.private_key = private_key
        self.cert_pem = None
        self.ca_pub_pem = None
        self.peer = None
        self.token_manager = None
        self.ledger_request_id = None
        self.ledger = None
        self.auctions = {
                            "last_auction_id": 0,
                            "auction_list": {},
                            "my_auctions": {},
                        }
                        
        

""" Example

[
    {
    "last_auction_id": 0,
    "auction_list": {
                        1: { "highest_bid": 150, "my_bid": False },
                        2: { "highest_bid": 230, "my_bid": True },
                    }
    }
] 

"""