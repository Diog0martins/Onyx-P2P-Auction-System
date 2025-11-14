import json
import uuid

from fastapi import FastAPI, HTTPException, Request

from ca.ca_utils.time import now_iso
from ca.ca_db import get_db
from ca.ca_api.Register import RegisterReq, RegisterResp
from ca.ca_api.Tokens import TokensReq, TokensResp

from crypto.encoding.b64 import b64e, b64d
from crypto.certificates.certificates import make_certificate

from crypto.keys.keys_crypto import get_pub_bytes, load_rsa_public_key

# Instancia o serviço FastAPI
app = FastAPI(title="Auction CA", version="1.0.0")


# Endpoint simples de ‘health’ check para monitorização
@app.get("/health")
def health():
    return {"status": "ok", "time": now_iso()}


# Expõe a chave pública da CA em base64
@app.get("/ca_pub")
def ca_pub(request: Request):

    ca_vk = request.app.state.CA_VK
    ca_pub_bytes = get_pub_bytes(ca_vk)
    return {"ca_pub": b64e(ca_pub_bytes)}


# Valida user_pub, gera uid, cria cert
@app.post("/register", response_model=RegisterResp)
def register(req: RegisterReq, request: Request):
    try:
        pub_b64 = req.user_pub
        vk = load_rsa_public_key(b64d(pub_b64))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid RSA public key (PEM/base64 expected).")

    uid = str(uuid.uuid4())
    cert, cert_sig = make_certificate(uid, req.user_pub, {"display_name": req.display_name} if req.display_name else {}, request.app.state.CA_SK)

    conn = get_db(request.app.state.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(uid, user_pub, cert_json, cert_sig, created_at, token_quota) VALUES(?,?,?,?,?,?)",
        (uid, req.user_pub, json.dumps(cert, separators=(",", ":"), sort_keys=True), cert_sig, now_iso(), 0)
    )
    conn.commit()
    conn.close()

    return RegisterResp(
        uid=uid,
        cert=cert,
        cert_sig=cert_sig,
        ca_pub= b64e(get_pub_bytes(request.app.state.CA_VK)),
        token_quota=0
    )


# Verifica se uid existe, gera count UUIDs, incrementa contador em users.token_quota
@app.post("/tokens", response_model=TokensResp)
def issue_tokens(req: TokensReq):
    conn = get_db()
    cur = conn.cursor()

    row = cur.execute("SELECT uid FROM users WHERE uid=?", (req.uid,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Unknown uid")

    issued = []
    now = now_iso()
    for _ in range(req.count):
        tid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO tokens(token_id, uid, issued_at, used) VALUES(?,?,?,0)",
            (tid, req.uid, now)
        )
        issued.append(tid)

    cur.execute("UPDATE users SET token_quota = token_quota + ? WHERE uid=?", (req.count, req.uid))
    conn.commit()
    conn.close()

    return TokensResp(uid=req.uid, issued=issued)