import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("quota.db")

# Use WAL mode for better concurrency
def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")

        # Global quota
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quota (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                max_images INTEGER NOT NULL,
                sent_images INTEGER NOT NULL
            )
        """)

        # Per-user final receive tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sent_users (
                phone TEXT PRIMARY KEY
            )
        """)

        # User conversation state
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                phone TEXT PRIMARY KEY,
                name TEXT,
                state TEXT NOT NULL
            )
        """)

        # Initialize quota row if missing
        cur.execute("SELECT COUNT(*) FROM quota")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO quota (id, max_images, sent_images) VALUES (1, 100, 0)"
            )
        conn.commit()


@contextmanager
def get_conn():
    """Provide a thread-safe connection using WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)  # autocommit off for transactions
    try:
        yield conn
    finally:
        conn.close()


def get_quota():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT max_images, sent_images FROM quota WHERE id = 1")
        return cur.fetchone()  # (max_images, sent_images)


def increment_sent():
    with get_conn() as conn:
        cur = conn.cursor()
        # Lock the row for this transaction to prevent race
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT sent_images, max_images FROM quota WHERE id = 1")
        sent_images, max_images = cur.fetchone()
        if sent_images < max_images:
            cur.execute("UPDATE quota SET sent_images = sent_images + 1 WHERE id = 1")
            conn.commit()
            return True
        else:
            conn.rollback()
            return False


def update_max_quota(value: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE quota SET max_images = ? WHERE id = 1", (value,))
        conn.commit()


def has_user_received(phone: str) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sent_users WHERE phone = ?", (phone,))
        return cur.fetchone() is not None


def mark_user_received(phone: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO sent_users (phone) VALUES (?)", (phone,))
        conn.commit()


def can_send_image() -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT max_images, sent_images FROM quota WHERE id = 1")
        max_images, sent_images = cur.fetchone()
        return sent_images < max_images


def get_user(phone: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, state FROM users WHERE phone = ?", (phone,))
        return cur.fetchone()  # (name, state) or None


def upsert_user(phone: str, state: str, name: str | None = None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (phone, name, state)
            VALUES (?, ?, ?)
            ON CONFLICT(phone)
            DO UPDATE SET
                state = excluded.state,
                name = COALESCE(excluded.name, users.name)
        """, (phone, name, state))
        conn.commit()
