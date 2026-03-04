import requests
import time
from client.ca_handler.ca_info import CA_URL

TARGET_ENDPOINT = f"{CA_URL}/reveal_identity"

def simulate_reveal_abuse():
    print(f"Reveal Abuse Test attack: {TARGET_ENDPOINT}")

    payload = {
        "encrypted_identity": "invalid_blob_forged_by_attacker",
        "token_id_disputed": "fake_token_id_123",
        "requester_uid": "malicious_user_007"
    }

    for i in range(10):
        try:
            print(f"Try number {i + 1}")
            response = requests.post(TARGET_ENDPOINT, json=payload)
            print(f"CA response: {response.status_code} - {response.text}")
            time.sleep(0.5)
        except Exception as e:
            print(f"Erro: {e}")


if __name__ == "__main__":
    simulate_reveal_abuse()