import json
from pathlib import Path


CONFIG_DIR = Path.cwd() / "user"

def load_ledger():
    ledger_file = CONFIG_DIR / "ledger.json"
    if ledger_file.exists():
        with ledger_file.open("r") as f:
            return json.load(f)
    return []

def save_ledger(ledger):
    ledger_file = CONFIG_DIR / "ledger.json"
    with ledger_file.open("w") as f:
        json.dump(ledger, f, indent=4)