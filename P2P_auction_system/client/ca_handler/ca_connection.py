import sys
import json
import base64
import requests
from design.ui import UI
from crypto.encoding.b64 import b64e, b64d
from crypto.certificates.certificates import create_x509_csr
from crypto.crypt_decrypt.decrypt import decrypt_with_private_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from client.ca_handler.ca_info import CA_URL


# =============  Registration & Setup ============= 

def connect_and_register_to_ca(client):
    """
    Establishes the initial trust with the CA. Performs a health check, submits a 
    Certificate Signing Request (CSR) for identity verification, and decrypts the 
    returned secrets (Group Key) using the peer's private key.
    """
    
    # 1. Health Check
    try:
        health_resp = requests.get(f"{CA_URL}/health", timeout=3)
        health_resp.raise_for_status()
        
        UI.step("CA Service Status", "ONLINE") 
        
    except Exception as e:
        UI.error(f"CA unavailable at {CA_URL}")
        UI.sub_info("Details", str(e))
        sys.exit(1)

    # 2. Build X.509 CSR (Certificate Signing Request)
    try:
        csr_pem = create_x509_csr(
            private_key=client.private_key,
            public_key=client.public_key,
            common_name="AnonymousPeer",
            meta={"display_name": "P2P User"}
        )
    except Exception as e:
        UI.error(f"Failed to create certificate CSR: {e}")
        sys.exit(1)

    payload = {
        "csr_pem_b64": b64e(csr_pem)
    }

    # 3. Registration Request
    try:
        resp = requests.post(f"{CA_URL}/register", json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        UI.error(f"Registration rejected by CA")
        UI.sub_info("Reason", str(e))
        sys.exit(1)

    data = resp.json()

    # 4. Decrypt Secrets (Group Key)
    try:
        encrypted_blob = b64d(data["encrypted_secrets_b64"])

        private_key_pem = client.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )

        decrypted_json_bytes = decrypt_with_private_key(encrypted_blob, private_key_pem)
        secrets = json.loads(decrypted_json_bytes.decode('utf-8'))

        group_key = b64d(secrets["group_key"])
        session_key = b64d(secrets["session_key"])

        client.ca_session_key = session_key

        UI.step("Secure Channel", "ESTABLISHED")

    except Exception as e:
        UI.error(f"Failed to decrypt CA secrets: {e}")
        sys.exit(1)

    return {
        "uid": data["uid"],
        "cert_pem": b64d(data["cert_pem_b64"]),
        "ca_pub_pem": b64d(data["ca_pub_pem_b64"]),
        "group_key": group_key,
        "token_quota": data["token_quota"],
    }


# =============  Identity Disclosure ============= 

def request_winner_reveal(client, token_id, encrypted_identity_blob):
    """
    Contacts the CA to securely decrypt the 'Encrypted Identity Package' bound to a 
    specific token. Used for dispute resolution or validating a winner's identity.
    """
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

        # Verify CA Signature on the Receipt
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