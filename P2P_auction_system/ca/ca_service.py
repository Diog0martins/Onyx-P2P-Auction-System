import base64
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

import sys
import uvicorn

from config.config import parse_config_file
from local_test import TEST

# Definem caminhos para a base de dados SQLite e apra os ficheiros com a chave
# privada e pública da CA.
DB_PATH = os.environ.get("CA_DB_PATH", "ca.db")
CA_SK_PATH = os.environ.get("CA_SK_PATH", "ca_ed25519_sk.pem")
CA_PK_PATH = os.environ.get("CA_PK_PATH", "ca_ed25519_pk.pem")

CA_SK = ""
CA_VK = ""

# Converte dicionário Python em JSON
def canonical_bytes(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

# Codificam base64
def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

# Descodificam base64
def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))

# Introduz time-stamps
def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# Introduz time-stamps
def iso_in_days(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()

# Se existirem ficheiros ca_ed25519_sk.pem e ca_ed25519_pk.pem, lê-os
# Caso contrário, gera um novo par Ed25519 e persiste-os nesses ficheiros.
def ensure_ca_keys():
    if os.path.exists(CA_SK_PATH) and os.path.exists(CA_PK_PATH):
        with open(CA_SK_PATH, "rb") as f:
            sk_bytes = f.read()
        with open(CA_PK_PATH, "rb") as f:
            pk_bytes = f.read()
        sk = SigningKey(sk_bytes)
        vk = VerifyKey(pk_bytes)
        return sk, vk

    sk = SigningKey.generate()
    vk = sk.verify_key
    with open(CA_SK_PATH, "wb") as f:
        f.write(bytes(sk))
    with open(CA_PK_PATH, "wb") as f:
        f.write(bytes(vk))
    return sk, vk


# Cria uma conexão a ca.db
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Cria as tabelas se não existirem
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            user_pub TEXT NOT NULL,
            cert_json TEXT NOT NULL,
            cert_sig TEXT NOT NULL,
            created_at TEXT NOT NULL,
            token_quota INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token_id TEXT PRIMARY KEY,
            uid TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(uid) REFERENCES users(uid)
        )
    """)
    conn.commit()
    conn.close()


# Entra no /register
class RegisterReq(BaseModel):
    user_pub: str = Field(..., description="Ed25519 public key (base64, 32 bytes)")
    display_name: Optional[str] = Field(None, description="Optional metadata")

# Sai do /register
class RegisterResp(BaseModel):
    uid: str
    cert: dict
    cert_sig: str
    ca_pub: str
    token_quota: int

# Entra no /tokens
class TokensReq(BaseModel):
    uid: str
    count: int = Field(ge=1, le=100)

# Sai do /tokens
class TokensResp(BaseModel):
    uid: str
    issued: List[str]

# Monta um cert
def make_certificate(uid: str, user_pub: str, meta: Optional[dict]) -> (dict, str):
    cert = {
        "uid": uid,
        "user_pub": user_pub,
        "issued_at": now_iso(),
        "expiry": iso_in_days(180),
        "meta": meta or {}
    }
    sig = CA_SK.sign(canonical_bytes(cert)).signature
    return cert, b64e(sig)

# Verifica o cert
def verify_certificate(cert: dict, cert_sig_b64: str) -> bool:
    try:
        CA_VK.verify(canonical_bytes(cert), b64d(cert_sig_b64))
        return True
    except BadSignatureError:
        return False

# Instancia o serviço FastAPI
app = FastAPI(title="Auction CA", version="1.0.0")

# Endpoint simples de ‘health’ check para monitorização
@app.get("/health")
def health():
    return {"status": "ok", "time": now_iso()}

# Expõe a chave pública da CA em base64
@app.get("/ca_pub")
def ca_pub():
    return {"ca_pub": b64e(bytes(CA_VK))}

# Valida user_pub, gera uid, cria cert
@app.post("/register", response_model=RegisterResp)
def register(req: RegisterReq):
    try:
        vk = VerifyKey(b64d(req.user_pub))
        _ = bytes(vk)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Ed25519 public key (base64 expected, 32 bytes).")

    uid = str(uuid.uuid4())
    cert, cert_sig = make_certificate(uid, req.user_pub, {"display_name": req.display_name} if req.display_name else {})

    conn = get_db()
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
        ca_pub=b64e(bytes(CA_VK)),
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

def prepare_ca():
    global CA_SK
    global CA_VK
    CA_SK, CA_VK = ensure_ca_keys()
    init_db()

def run_ca():
    if TEST != 1:
        print(f"[CA] TEST != 1 (TEST={TEST}). CA não será iniciada neste modo.")
        sys.exit(0)

    host, port = parse_config_file("configCA/configCA.json")

    print(f"[CA] A iniciar CA em {host}:{port} (TEST={TEST})")

    prepare_ca()

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
    )