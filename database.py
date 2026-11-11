# database.py - Users - Hashed passwords
import sqlite3, hashlib, os
DB = "nexa_users.db"
def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
    conn.commit(); conn.close()
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def create_user(username, password):
    try:
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO users VALUES (?, ?)", (username.strip(), hash_pw(password)))
        conn.commit(); conn.close(); return True
    except: return False
def check_user(username, password):
    conn = sqlite3.connect(DB)
    cur = conn.execute("SELECT password FROM users WHERE username=?", (username.strip(),))
    row = cur.fetchone(); conn.close()
    return row is not None and row[0] == hash_pw(password)