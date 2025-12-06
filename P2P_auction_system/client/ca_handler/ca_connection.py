import base64
import sys
import json
import requests

from crypto.certificates.certificates import create_x509_csr
from crypto.encoding.b64 import b64e, b64d
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# ----- CA information hard-coded -----
CA_IP = "127.0.0.1"
CA_PORT = 8443
CA_URL = f"http://{CA_IP}:{CA_PORT}"


def connect_and_register_to_ca(client):

    # 1) Health check
    try:
        health_resp = requests.get(f"{CA_URL}/health", timeout=3)
        health_resp.raise_for_status()
        print(f"[CA] Health OK -> {health_resp.json()}")
    except Exception as e:
        print(f"[CA] Error contacting CA: {e}")
        sys.exit(1)

    # 2) Use existing keys -> build X.509 CSR
    try:
        csr_pem = create_x509_csr(
            private_key=client.private_key,
            public_key=client.public_key,
            common_name="AnonymousPeer",      # goes into CSR subject CN
            meta={"display_name": "P2P User"}
        )
    except Exception as e:
        print(f"[Client] Failed to create certificate: {e}")
        sys.exit(1)

    payload = {
        "csr_pem_b64": b64e(csr_pem)
    }

    # 3) Send CSR to CA
    try:
        resp = requests.post(f"{CA_URL}/register", json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"[CA] Error calling /register: {e}")
        sys.exit(1)

    data = resp.json()
    print(f"    [CA] Registration complete. UID = {data['uid']}")

    # 4) Return everything the CA gave back
    return {
        "uid": data["uid"],
        "cert_pem": b64d(data["cert_pem_b64"]),
        "ca_pub_pem": b64d(data["ca_pub_pem_b64"]),
        "group_key": b64d(data["group_key_b64"]),
        "token_quota": data["token_quota"],
    }

def request_winner_reveal(client, token_id, encrypted_identity_blob):
    print(f"[Security] Requesting identity disclosure for the token: {token_id}...")

    payload = {
        "encrypted_identity": encrypted_identity_blob,
        "token_id_disputed": token_id,
        "requester_uid": client.uuid
    }

    try:
        resp = requests.post(f"{CA_URL}/reveal_identity", json=payload, timeout=10)
        resp.raise_for_status()

        response_json = resp.json()
        receipt_data = response_json["receipt_data"]
        signature_b64 = response_json["signature_b64"]
        signature = base64.b64decode(signature_b64)

        # Verificar assinatura da CA
        data_bytes = json.dumps(
            receipt_data,
            sort_keys=True,
            separators=(',', ':')
        ).encode('utf-8')

        pem_data = client.ca_pub_pem
        if isinstance(pem_data, str):
            pem_data = pem_data.encode('utf-8')

        ca_pub_key = serialization.load_pem_public_key(pem_data)

        ca_pub_key.verify(
            signature,
            data_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        print("[Security] VALID CA SIGNATURE! Identity confirmed.")
        print(f" -> Actual Winner (UID): {receipt_data['real_uid']}")
        return receipt_data

    except Exception as e:
        print(f"[!] CRITICAL FAILURE IN CA VALIDATION: {e}")
        return None