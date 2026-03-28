import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- CONNECT ---------------- #
def connect():
    return sqlite3.connect("users.db")


# ---------------- INIT DB ---------------- #
def init_db():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        unlocked_level INTEGER DEFAULT 1
    )
    """)

    conn.commit()
    conn.close()


# ---------------- REGISTER USER ---------------- #
def create_user(username, password):
    conn = connect()
    c = conn.cursor()

    hashed_password = generate_password_hash(password)

    try:
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
    except:
        conn.close()
        return False

    conn.close()
    return True


# ---------------- LOGIN USER ---------------- #
def get_user(username, password):
    conn = connect()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    )

    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[2], password):
        return user

    return None


# ---------------- GET LEVEL ---------------- #
def get_level(username):
    conn = connect()
    c = conn.cursor()

    c.execute(
        "SELECT unlocked_level FROM users WHERE username=?",
        (username,)
    )

    result = c.fetchone()
    conn.close()

    if result:
        return result[0]

    return 1


# ---------------- UNLOCK LEVEL ---------------- #
def unlock_level(username, new_level):
    conn = connect()
    c = conn.cursor()

    c.execute(
        "UPDATE users SET unlocked_level=? WHERE username=?",
        (new_level, username)
    )

    conn.commit()
    conn.close()