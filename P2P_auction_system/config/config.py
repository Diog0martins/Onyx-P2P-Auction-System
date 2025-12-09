import json, os
from pathlib import Path

CONFIG_DIR = Path.cwd() / "config"

def make_json_path(path):
    """
        Constructs the expected JSON file path based on the directory name.

        It assumes a naming convention where the configuration file has the same name
        as its parent folder (e.g., input 'config1' becomes 'config1/config1.json').

        Args:
            path (str): The relative path or directory name of the configuration.

        Returns:
            str: The constructed path to the JSON file.
    """

    last_part = os.path.basename(path)
    new_path = os.path.join(path, f"{last_part}.json")
    
    return new_path

def parse_config_file(config_file):
    """
        Opens and reads a specific JSON configuration file from the global CONFIG_DIR.

        Args:
            config_file (str): The relative path to the JSON file (e.g., 'config1/config1.json').

        Returns:
            tuple: A tuple containing (host, port). Port is an integer, or None if missing.
    """

    with open(CONFIG_DIR / config_file) as fp:
        content = json.load(fp)

    host = content.get("host")
    port = int(content["port"]) if "port" in content else None

    return host, port

def parse_config(config_path):
    """
        Main entry point for loading configuration settings.

        It orchestrates the process by first resolving the JSON filename using
        "make_json_path" and then parsing the file contents.

        Args:
            config_path (str): The configuration identifier (e.g., 'config1').

        Returns:
            tuple: The (host, port) loaded from the file.
    """

    config_file = make_json_path(config_path)
    return parse_config_file(config_file)