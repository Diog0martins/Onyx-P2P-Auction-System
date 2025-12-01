import requests, json
from crypto.encoding.b64 import b64d

CA_IP = "127.0.0.1"
CA_PORT = 8443
CA_URL = f"http://{CA_IP}:{CA_PORT}"

def get_valid_timestamp():
    try:
        response = requests.get(f"{CA_URL}/timestamp")
        response.raise_for_status()
        
        data = response.json()
        
        return data["timestamp"], b64d(data["signature"])

    except Exception as e:
        print(f"Error fetching timestamp: {e}")
        return None
    
def leave_network(uid):
    try:
        payload = {"uid": uid}
        
        response = requests.post(f"{CA_URL}/leave", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"Successfully left. New Group Key received.")
        
        return data["new_keys"]

    except Exception as e:
        print(f"Error leaving network: {e}")
        return "{}"