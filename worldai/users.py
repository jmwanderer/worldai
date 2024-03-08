"""
Functions to access and manage the user table.
"""
import os
import time

# add user(name) --> AUTH KEY
# lookup auth (auth key) --> ID

def add_user(db, username: str) -> str:
    user_id = os.urandom(4).hex()
    auth_key = os.urandom(12).hex()
    now = time.time()
    c = db.cursor()
    c.execute(
        "INSERT INTO users (id, username, auth_key, created, accessed) VALUES (?, ?, ?, ?, ?)", 
        (user_id, username, auth_key, now, now)
    )
    db.commit()
    return auth_key

def find_by_auth_key(db, auth_key: str) -> str|None:
    c = db.cursor()
    q = c.execute("SELECT id, username FROM users WHERE auth_key = ?", (auth_key,))
    r = q.fetchone()
    if r is None:
        return None
    (user_id, username) = r
    now = time.time()
    c.execute("UPDATE users SET accessed = ? WHERE id = ?", (now, user_id))
    db.commit()
    return user_id

def get_auth_key(db, user_id: str) -> str|None:
    c = db.cursor()
    q = c.execute("SELECT auth_key FROM users WHERE id = ?",  (user_id,))
    r = q.fetchone()
    if r is None:
        return None
    return r[0]


 