import json, os
from pathlib import Path

CONFIG_DIR = Path.cwd() / "config"

def make_json_path(path):
    # Get the last part of the path (e.g., 'config1')
    last_part = os.path.basename(path)
    
    # Join it back to create the new file path
    new_path = os.path.join(path, f"{last_part}.json")
    
    return new_path

def parse_config_file(config_file):

    with open(CONFIG_DIR / config_file) as fp:
        content = json.load(fp)

    host = content.get("host")
    port = int(content["port"]) if "port" in content else None

    return host, port

def parse_config(config_path):
    config_file = make_json_path(config_path)
    return parse_config_file(config_file)