# ================================================================
# Informations
# ================================================================

import json
from pathlib import Path

CONFIG_DIR = Path.cwd() / "config"

def load_info(arg):
    """Load the information of the user"""
    info_file = CONFIG_DIR / arg / (arg + ".json")
    if info_file.exists():
        with info_file.open("r") as f:
            return json.load(f)
    return {}

def save_info_test(data, config):
    """Save the info of the user"""
    info_file = CONFIG_DIR / config / (config + ".json")
    with info_file.open("w") as f:
        json.dump(data, f, indent=4)

def create_info():
    user = {}
    print("Name:")
    user["name"] = input("> ").strip()
    print("Pass:")
    user["pass"] = input("> ").strip()
    print("Direction:")
    user["Direction"] = input("> ").strip()

    return user