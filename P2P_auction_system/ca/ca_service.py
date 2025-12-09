import os
import sys
import uvicorn
from pathlib import Path
from local_test import TEST
from ca.ca_db import init_db
from ca.ca_api.ca_api import app
from network.ip import get_ip
from config.config import parse_config_file
from crypto.keys.keys_handler import prepare_key_pair_generation


def prepare_ca(ca_path, db_path):
    ca_path = Path(ca_path)
    ca_sk, ca_vk = prepare_key_pair_generation(ca_path)
    init_db(db_path)

    return ca_sk, ca_vk


def run_ca():
    
    if TEST == 1:
        # print(f"[CA] TEST != 1 (TEST={TEST}). CA will not start in this mode.")
        # sys.exit(0)
        host, port = parse_config_file("configCA/configCA.json")

    else:
        host = get_ip()
        port = 8443

    print(f"[CA] Starting CA on {host}:{port}")

    app.state.DB_PATH = os.environ.get("CA_DB_PATH", "ca/ca.db")

    ca_sk, ca_vk = prepare_ca("config/configCA/", app.state.DB_PATH)

    app.state.CA_SK = ca_sk
    app.state.CA_VK = ca_vk
    app.state.KEY_GROUP_BOOL = False
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
    )