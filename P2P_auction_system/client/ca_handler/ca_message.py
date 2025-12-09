import base64
import requests
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding


CA_IP = "127.0.0.1"
CA_PORT = 8443
CA_URL = f"http://{CA_IP}:{CA_PORT}"


def get_valid_timestamp(delta_seconds=None):
    try:
        params = {}
        if delta_seconds is not None:
            params["delta"] = int(delta_seconds)

        response = requests.get(f"{CA_URL}/timestamp", params=params)
        response.raise_for_status()

        data = response.json()

        return data

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

def verify_timestamp_signature(ca_pub_pem, timestamp_data):
    try:
        if not timestamp_data:
            return False

        ts_iso = timestamp_data.get("timestamp")
        sig_b64 = timestamp_data.get("signature")

        if not ts_iso or not sig_b64:
            return False

        data_bytes = ts_iso.encode('utf-8')
        signature = base64.b64decode(sig_b64)

        if isinstance(ca_pub_pem, str):
            ca_pub_pem = ca_pub_pem.encode('utf-8')

        ca_pub_key = serialization.load_pem_public_key(ca_pub_pem)

        ca_pub_key.verify(
            signature,
            data_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True

    except Exception as e:
        print(f"[Security] Falha na verificação da assinatura do Timestamp: {e}")
        return False