import sqlite3

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