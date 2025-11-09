import json

def parse_config(config_file):

    with open(config_file) as fp:
        content = json.load(fp)
    
    return content["host"], int(content["port"])