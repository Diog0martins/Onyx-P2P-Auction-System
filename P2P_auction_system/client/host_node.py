import sys
from pathlib import Path
from design.ui import UI
from network.ip import get_ip
from network.peer import run_peer
from config.config import parse_config
from client.client_state import Client
from crypto.token.token_manager import TokenManager
from client.ledger.ledger_handler import init_cli_ledger
from crypto.keys.keys_handler import prepare_key_pair_generation
from client.ca_handler.ca_connection import connect_and_register_to_ca
from client.ledger.translation.ledger_to_dict import ledger_to_auction_dict


def check_user_path(user_path):
    if not user_path.exists():
        user_path.mkdir(parents=True, exist_ok=True)


def start_client(args):
    # 1. Print Banner
    UI.banner()

    # Verify if we are working in LAN or localhost
    if len(args) == 2:
        config = args[1]
        user_path = Path("config") / config / "user"
        host, port = parse_config(config)
        UI.step("Loading Configuration", "FILE")
        UI.sub_step("Source", f"config/{config}")
    
    else: 
        # LAN Case
        user_path = Path("user")
        host = get_ip()
        port = 6000
        # UI PRINT
        UI.step("Network Discovery", "LAN")
        UI.sub_step("Host IP", host)

    check_user_path(user_path)

    # Generate or get key pair
    private_key, public_key = prepare_key_pair_generation(user_path)
    UI.step("Cryptographic Identity", "LOADED")
    
    # Generate Client Object
    client = Client(user_path, public_key, private_key)

    # Send public key to CA
    try:
        info = connect_and_register_to_ca(client)
        
        client.uuid = info["uid"]
        client.cert_pem = info["cert_pem"]
        client.ca_pub_pem = info["ca_pub_pem"]
        client.group_key = info["group_key"]
        client.is_running = True
        
        UI.step("Certificate Authority", "REGISTERED")
        UI.sub_step("UID", f"{client.uuid[:8]}...") # Show short UID
    except Exception as e:
        UI.error(f"CA Connection failed: {e}")
        sys.exit(1)

    config_name = args[1] if len(args) == 2 else "config_lan"
    client.token_manager = TokenManager(
        config_name=config_name,
        ca_pub_pem=client.ca_pub_pem,
        uid=info["uid"]
    )

    # Get last used ledger
    init_cli_ledger(client, user_path)
    
    if not len(client.ledger.chain) == 1:
        client.auctions = ledger_to_auction_dict(client.ledger, client.token_manager)

    UI.step("Client structures", "SYNCED")
    UI.sub_step("Ledger", "Loaded")
    UI.sub_step("Token Manager", "Loaded")

    # Host Discovery and Connection Establishment
    run_peer(host, port, client)


