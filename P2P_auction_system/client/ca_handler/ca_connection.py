import base64
import sys

import requests
from nacl.signing import SigningKey

# ----- CA information hard-coded -----
CA_IP = "127.0.0.1"
CA_PORT = 8443
CA_URL = f"http://{CA_IP}:{CA_PORT}"


def connect_and_register_to_ca(display_name: str, client):
    
    try:
        health_resp = requests.get(f"{CA_URL}/health", timeout=3)
        health_resp.raise_for_status()
        print(f"[CA] Health OK -> {health_resp.json()}")
    except Exception as e:
        print(f"[CA] Erro a contactar CA em {CA_URL}/health: {e}")
        sys.exit(1)

    # 2) Gerar par de chaves Ed25519 para este cliente
    sk = SigningKey.generate()
    vk = sk.verify_key
    user_pub_b64 = base64.b64encode(bytes(vk)).decode("ascii")

    # 3) Preparar payload de registo
    payload = {
        "user_pub": user_pub_b64,
        "display_name": display_name,
    }

    # 4) Chamar /register na CA
    try:
        resp = requests.post(f"{CA_URL}/register", json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"[CA] Erro no /register: {e}")
        sys.exit(1)

    data = resp.json()
    uid = data["uid"]
    cert = data["cert"]
    cert_sig = data["cert_sig"]
    ca_pub = data["ca_pub"]

    print(f"[CA] Registo concluído com sucesso. UID = {uid}")

    return {
        "signing_key": sk,
        "verify_key": vk,
        "uid": uid,
        "cert": cert,
        "cert_sig": cert_sig,
        "ca_pub": ca_pub,
    }

