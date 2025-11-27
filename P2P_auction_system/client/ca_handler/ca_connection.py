import sys
import requests
import requests

from crypto.certificates.certificates import create_x509_csr
from crypto.encoding.b64 import b64e, b64d

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
            common_name="AnonymousPeer",
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
    print(f"[CA] Registration complete. UID = {data['uid']}")

    # 4) Return everything the CA gave back
    return {
        "uid": data["uid"],
        "cert_pem": b64d(data["cert_pem_b64"]),
        "ca_pub_pem": b64d(data["ca_pub_pem_b64"]),
        "token_quota": data["token_quota"],
    }
