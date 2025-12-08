import uuid
import json
from fastapi import FastAPI, HTTPException, Request
from typing import Optional
from datetime import datetime, timezone, timedelta

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from ca.ca_utils.time import now_iso
from ca.ca_db import get_db, store_user, user_exists, insert_token, increment_token_quota, remove_user_and_get_remaining_pubkeys
from ca.ca_api.Register import RegisterReq, RegisterResp
from ca.ca_api.Tokens import TokensReq, TokensResp

from crypto.encoding.b64 import b64e
from crypto.certificates.certificates import make_x509_certificate, verify_csr
from crypto.crypt_decrypt.crypt import encrypt_message_symmetric_gcm
from crypto.crypt_decrypt.hybrid import hybrid_decrypt
from crypto.crypt_decrypt.crypt import encrypt_with_public_key
from crypto.keys.keys_crypto import get_pub_bytes

from ca.ca_api.BlindTokens import BlindSignReq
from crypto.encoding.b64 import b64e, b64d

from crypto.keys.keys_crypto import generate_aes_key

from pydantic import BaseModel


# FastAPI Service Instance
app = FastAPI(title="Auction CA", version="1.0.0")

app.state.PEER_SESSIONS = {}

# Simple ‘health’ endpoint for monitoring check
@app.get("/health")
def health():

    return {"status": "ok", "time": now_iso()}



# Exposes b64 encoded CA public key
@app.get("/ca_pub")
def ca_pub(request: Request):
    
    ca_vk = request.app.state.CA_VK
    ca_pub_bytes = get_pub_bytes(ca_vk)
    
    return {"ca_pub": b64e(ca_pub_bytes)}



# Validates UserCertificate, generates uuid and signs certificate
@app.post("/register", response_model=RegisterResp)
def register(req: RegisterReq, request: Request):

    # 1 — decode & verify CSR
    try:
        csr = verify_csr(req.csr_pem_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSR")

    # 2 — assign UUID
    uid = str(uuid.uuid4())

    # 3 — create X.509 certificate
    cert_pem = make_x509_certificate(
        csr=csr,
        ca_sk=request.app.state.CA_SK
    )

    # 4 — store PEM cert in DB
    user_pub_bytes = get_pub_bytes(csr.public_key())
    store_user(
        request.app.state.DB_PATH,
        uid,
        req,
        user_pub_bytes,
        cert_pem
    )

    # 5 — group key
    if app.state.KEY_GROUP_BOOL is False:        
        group_key = generate_aes_key()
        app.state.KEY_GROUP_BOOL = True
        app.state.KEY_GROUP = group_key

    session_key = generate_aes_key()

    request.app.state.PEER_SESSIONS[uid] = session_key

    secrets_json = json.dumps({
        "group_key": b64e(request.app.state.KEY_GROUP),
        "session_key": b64e(session_key)
    })

    user_pub_pem = b64e(user_pub_bytes)
    encrypted_blob = encrypt_with_public_key(secrets_json.encode('utf-8'), user_pub_bytes)

    # 6 — Return seguro
    return RegisterResp(
        uid=uid,
        cert_pem_b64=b64e(cert_pem),
        ca_pub_pem_b64=b64e(get_pub_bytes(request.app.state.CA_VK)),
        encrypted_secrets_b64=b64e(encrypted_blob),  # <--- CAMPO SEGURO
        token_quota=0
    )





# Verify if uuid exists and generates count UUIDs, increments UserID token counting
# What should do:
# - send signed blinded token
# - send timestamp and signature
@app.post("/tokens", response_model=TokensResp)
def issue_tokens(req: TokensReq, request: Request):

    conn = get_db(request.app.state.DB_PATH)
    
    if not user_exists(conn, req.uid):
        conn.close()
        raise HTTPException(status_code=404, detail="Unknown uid")

    issued = []
    for _ in range(req.count):
        tid = insert_token(conn, req.uid)
        issued.append(tid)

    increment_token_quota(conn, req.uid, req.count)

    conn.commit()
    conn.close()

    return TokensResp(uid=req.uid, issued=issued)

@app.post("/blind_sign")
def blind_sign(req: BlindSignReq, request: Request):

    # 1. Verify that the UID exists
    conn = get_db(request.app.state.DB_PATH)
    if not user_exists(conn, req.uid):
        conn.close()
        raise HTTPException(status_code=404, detail="Unknown uid")
    conn.close()

    # 2. Obtain the CA private key
    ca_sk = request.app.state.CA_SK

    # 3. Decoding the blinded token
    blinded_int = int.from_bytes(b64d(req.blinded_token_b64), "big")

    # 4. RSA blind signing: signature = blinded^d mod n
    numbers = ca_sk.private_numbers()
    d = numbers.d
    n = numbers.public_numbers.n

    signature_int = pow(blinded_int, d, n)

    # 5. Convert to bytes for sending
    sig_bytes = signature_int.to_bytes((n.bit_length() + 7) // 8, "big")

    return {"blind_signature_b64": b64e(sig_bytes)}


@app.get("/timestamp")
def timestamp(request: Request, delta: Optional[int] = None):
    # 1. Calcular o tempo
    now = datetime.now(timezone.utc)

    if delta is not None:
        target_time = now + timedelta(seconds=delta)
    else:
        target_time = now

    # 2. Formatar para ISO String
    ts = target_time.replace(microsecond=0).isoformat()
    ts_bytes = ts.encode('utf-8')

    # 3. Get CA Private Key
    ca_sk = request.app.state.CA_SK

    # 4. Sign the timestamp
    signature = ca_sk.sign(
        ts_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    # 5. Return timestamp and signature
    return {
        "timestamp": ts,
        "signature": b64e(signature)
    }

@app.post("/leave")
def leave_network(req: dict, request: Request):

    uid = req["uid"]
    
    # 1. Database operations
    conn = get_db(request.app.state.DB_PATH)
    
    # This deletes the user and returns list of PEM strings for others
    remaining_pub_pems = remove_user_and_get_remaining_pubkeys(conn, uid)
    conn.close()

    # 2. Generate new AES Group Key
    new_group_key = generate_aes_key() # Usually returns a Base64 string

    encrypted_key_list = []

    # 3. Encrypt for each remaining user
    for pem_str in remaining_pub_pems:
        # Load the public key
        pub_key = serialization.load_pem_public_key(
            pem_str
        )
        # RSA Encrypt (OAEP + SHA256)
        ciphertext = pub_key.encrypt(
            new_group_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        encrypted_key_list.append(b64e(ciphertext))

    old_key = app.state.KEY_GROUP

    # 4. Update Server State
    app.state.KEY_GROUP = new_group_key

    answer = {
        "type": "new_key",
        "encrypted_keys": encrypted_key_list, 
    }

    to_send = json.dumps(answer)

    return{
        "new_keys": encrypt_message_symmetric_gcm(to_send, old_key)
    } 


class RevealReq(BaseModel):
    encrypted_identity: str
    token_id_disputed: str
    requester_uid: str

@app.post("/reveal_identity")
def reveal_identity(req: RevealReq, request: Request):
    ca_sk = request.app.state.CA_SK

    identity_pkg = hybrid_decrypt(req.encrypted_identity, ca_sk)

    if not identity_pkg:
        raise HTTPException(status_code=400, detail="Decryption failed")

    if identity_pkg.get("token_id_bound") != req.token_id_disputed:
        raise HTTPException(status_code=400, detail="Token mismatch! Fraud detected.")

    receipt_data = {
        "status": "REVEALED",
        "token_id": req.token_id_disputed,
        "real_uid": identity_pkg["real_uid"],
        "certificate_pem": identity_pkg["cert_pem_b64"],
        "timestamp": now_iso()
    }

    data_bytes = json.dumps(receipt_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

    signature = ca_sk.sign(
        data_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    return {
        "receipt_data": receipt_data,
        "signature_b64": b64e(signature)
    }
