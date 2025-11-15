import json
import uuid

from fastapi import FastAPI, HTTPException, Request

from ca.ca_utils.time import now_iso
from ca.ca_db import get_db, store_user, user_exists, insert_token, increment_token_quota
from ca.ca_api.Register import RegisterReq, RegisterResp
from ca.ca_api.Tokens import TokensReq, TokensResp

from crypto.encoding.b64 import b64e
from crypto.certificates.certificates import make_x509_certificate, verify_csr

from crypto.keys.keys_crypto import get_pub_bytes


# FastAPI Service Instance
app = FastAPI(title="Auction CA", version="1.0.0")



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
    store_user(
        request.app.state.DB_PATH,
        uid,
        req,
        get_pub_bytes(csr.public_key()),
        cert_pem
    )

    # 5 — return cert + CA public key
    return RegisterResp(
        uid=uid,
        cert_pem_b64=b64e(cert_pem),
        ca_pub_pem_b64=b64e(get_pub_bytes(request.app.state.CA_VK)),
        token_quota=0
    )





# Verify if uuid exists and generates count UUIDs, increments UserID token counting
# What should do:
# - send signed blinded token
# - send timestamp and signature
@app.post("/tokens", response_model=TokensResp)
def issue_tokens(req: TokensReq):

    conn = get_db()
    
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