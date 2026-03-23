import sqlite3

def init_db():

    conn = sqlite3.connect("progress.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS progress(
        id INTEGER PRIMARY KEY,
        unlocked INTEGER
    )
    """)

    c.execute("SELECT * FROM progress")

    if c.fetchone() is None:
        c.execute("INSERT INTO progress VALUES(1,1)")

    conn.commit()
    conn.close()


def get_level():

    conn = sqlite3.connect("progress.db")
    c = conn.cursor()

    c.execute("SELECT unlocked FROM progress WHERE id=1")

    level = c.fetchone()[0]

    conn.close()

    return level


def unlock_level():

    conn = sqlite3.connect("progress.db")
    c = conn.cursor()

    c.execute("UPDATE progress SET unlocked = unlocked + 1 WHERE id=1")

    conn.commit()
    conn.close()