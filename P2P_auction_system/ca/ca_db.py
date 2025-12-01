import sqlite3
import uuid
from ca.ca_utils.time import now_iso

# ====== Token Related Queries ======

def user_exists(conn, uid: str) -> bool:
    cur = conn.cursor()
    row = cur.execute("SELECT uid FROM users WHERE uid=?", (uid,)).fetchone()
    return row is not None


def insert_token(conn, uid: str) -> str:
    cur = conn.cursor()
    tid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO tokens(token_id, uid, issued_at, used) VALUES(?,?,?,0)",
        (tid, uid, now_iso())
    )
    return tid


def increment_token_quota(conn, uid: str, amount: int):
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET token_quota = token_quota + ? WHERE uid=?",
        (amount, uid)
    )

# ====== ====== ======


# ====== User Related Queries ======

def store_user(db_path, uid, req, csr_pem: bytes, cert_pem: bytes):
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(uid, user_pub_pem, csr_pem, cert_pem, created_at, token_quota) VALUES(?,?,?,?,?,?)",
        (uid,
         csr_pem,
         csr_pem,
         cert_pem,
         now_iso(),
         0)
    )
    conn.commit()
    conn.close()


def remove_user_and_get_remaining_pubkeys(conn, uid: str):
    cur = conn.cursor()
    
    cur.execute("DELETE FROM users WHERE uid=?", (uid,))
    
    rows = cur.execute("SELECT user_pub_pem FROM users").fetchall()
    
    pub_keys = [row[0] for row in rows]
    
    conn.commit()
    
    return pub_keys

# ====== ====== ======



# ====== Database Setup ======

# Cria uma conexão a ca.db
def get_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Cria as tabelas se não existirem
def init_db(db_path):
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            user_pub_pem TEXT NOT NULL,
            csr_pem TEXT NOT NULL,
            cert_pem TEXT NOT NULL,
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

# ====== ====== ======
