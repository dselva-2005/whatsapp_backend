import sqlite3
from pathlib import Path

DB_PATH = Path("quota.db")


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quota (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_images INTEGER NOT NULL,
            sent_images INTEGER NOT NULL
        )
    """)

    cur.execute("SELECT COUNT(*) FROM quota")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO quota (id, max_images, sent_images) VALUES (1, 100, 0)"
        )

    conn.commit()
    conn.close()


def get_quota():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT max_images, sent_images FROM quota WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return row  # (max_images, sent_images)


def increment_sent():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE quota SET sent_images = sent_images + 1 WHERE id = 1")
    conn.commit()
    conn.close()


def update_max_quota(value: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE quota SET max_images = ? WHERE id = 1",
        (value,)
    )
    conn.commit()
    conn.close()
