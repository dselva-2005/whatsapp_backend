import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("sqlite.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quota (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_images INTEGER NOT NULL,
            images_sent INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cur = conn.execute("SELECT COUNT(*) FROM quota")
    if cur.fetchone()[0] == 0:
        conn.execute(
            """
            INSERT INTO quota (id, max_images, images_sent, updated_at)
            VALUES (1, 100, 0, ?)
            """,
            (datetime.utcnow().isoformat(),),
        )

    conn.commit()
    conn.close()


def get_quota():
    conn = get_db()
    row = conn.execute("SELECT * FROM quota WHERE id = 1").fetchone()
    conn.close()
    return dict(row)


def update_quota(max_images: int):
    conn = get_db()
    conn.execute(
        """
        UPDATE quota
        SET max_images = ?, updated_at = ?
        WHERE id = 1
        """,
        (max_images, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def increment_usage():
    conn = get_db()
    conn.execute(
        """
        UPDATE quota
        SET images_sent = images_sent + 1,
            updated_at = ?
        WHERE id = 1
        """,
        (datetime.utcnow().isoformat(),),
    )
    conn.commit()
    conn.close()
