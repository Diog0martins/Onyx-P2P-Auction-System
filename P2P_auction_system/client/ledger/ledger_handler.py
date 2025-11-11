import json
from pathlib import Path


CONFIG_DIR = Path.cwd() / "config"

def load_public_ledger(config):
    ledger_file = CONFIG_DIR / config / "public_ledger.json"
    if ledger_file.exists():
        with ledger_file.open("r") as f:
            return json.load(f)
    return []

def load_local_ledger(config):
    ledger_file = CONFIG_DIR / config / "local_ledger.json"
    if ledger_file.exists():
        with ledger_file.open("r") as f:
            return json.load(f)
    return []

def save_public_ledger(ledger, config):
    ledger_file = CONFIG_DIR / config / "public_ledger.json"
    with ledger_file.open("w") as f:
        json.dump(ledger, f, indent=4)

def save_local_ledger(ledger, config):
    ledger_file = CONFIG_DIR / config / "local_ledger.json"
    with ledger_file.open("w") as f:
        json.dump(ledger, f, indent=4)