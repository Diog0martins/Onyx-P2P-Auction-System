class Client:
    def __init__(self, public_key, private_key):
        self.public_key = public_key
        self.private_key = private_key
        self.cert_pem = None
        self.ca_pub_pem = None
        self.token_manager = None