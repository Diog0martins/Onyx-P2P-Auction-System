from pathlib import Path
from network.peer import run_peer
from network.ip import get_ip
from config.config import parse_config
from crypto.keys.keys_handler import prepare_key_pair_generation
from client.client_state import Client 
from client.ca_handler.ca_connection import connect_and_register_to_ca
from crypto.token.token_manager import TokenManager
from client.ledger.ledger_handler import init_cli_ledger
from client.ledger.translation.ledger_to_dict import ledger_to_auction_dict


def check_user_path(user_path):
    if not user_path.exists():
        user_path.mkdir(parents=True, exist_ok=True)


def start_client(args):
    # Verify if we are working in LAN or localhost
    if len(args) == 2:
        config = args[1]
        user_path = Path("config") / config / "user"
        print("Peer info fetched from config file")
        host, port = parse_config(config)
    
    else: 
        #LAN Case -> For the Future
        user_path = Path("user")
        host = get_ip()
        port = 6000
        print("LAN Case: Not implemented!")

    check_user_path(user_path)

    # Generate or get key pair for further validation[ /user folder]
    private_key, public_key = prepare_key_pair_generation(user_path)

    # Generate Client Object
    client = Client(user_path, public_key, private_key)

    # Send public key ao CA
    info = connect_and_register_to_ca(client)

    client.uuid = info["uid"]
    client.cert_pem = info["cert_pem"]
    client.ca_pub_pem = info["ca_pub_pem"]
    client.group_key = info["group_key"]
    client.is_running = True


    config_name = args[1] if len(args) == 2 else "config_lan"
    client.token_manager = TokenManager(
        config_name=config_name,
        ca_pub_pem=client.ca_pub_pem,
        uid=info["uid"]
    )

    #Get last used ledger
    init_cli_ledger(client, user_path)

    if not len(client.ledger.chain) == 1:
        client.auctions = ledger_to_auction_dict(client.ledger)


    print(f"[Client] Token Manager inicializado para {config_name}")


    # Host Discovery and Connection Establishment
    run_peer(host, port, client)


