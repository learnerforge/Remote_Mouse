import sqlite3
import json
import time
import uuid
import logging
from pathlib import Path

logger = logging.getLogger("touchmorph.session")

DB_PATH = Path(__file__).resolve().parent / "touchmorph.db"


def _init():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            device_name TEXT,
            ip TEXT,
            paired INTEGER DEFAULT 0,
            mode TEXT DEFAULT 'mouse',
            last_active REAL,
            created REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            event TEXT,
            ts REAL
        )
    """)
    conn.commit()
    conn.close()


_init()


def create_session(device_name="", ip="") -> str:
    token = str(uuid.uuid4())
    now = time.time()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT OR REPLACE INTO sessions (token, device_name, ip, paired, mode, last_active, created) VALUES (?, ?, ?, 0, 'mouse', ?, ?)",
        (token, device_name, ip, now, now),
    )
    conn.commit()
    conn.close()
    return token


def restore_session(token: str) -> dict | None:
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT token, device_name, ip, paired, mode, last_active FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "token": row[0],
            "device_name": row[1],
            "ip": row[2],
            "paired": bool(row[3]),
            "mode": row[4],
            "last_active": row[5],
        }
    return None


def update_session(token: str, **kwargs):
    conn = sqlite3.connect(str(DB_PATH))
    fields = []
    vals = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        vals.append(v)
    if fields:
        vals.append(token)
        conn.execute(f"UPDATE sessions SET {', '.join(fields)} WHERE token = ?", vals)
        conn.commit()
    conn.close()


def touch_session(token: str):
    update_session(token, last_active=time.time())


def list_sessions() -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT token, device_name, ip, paired, mode, last_active FROM sessions ORDER BY last_active DESC"
    ).fetchall()
    conn.close()
    return [
        {
            "token": r[0],
            "device_name": r[1],
            "ip": r[2],
            "paired": bool(r[3]),
            "mode": r[4],
            "last_active": r[5],
        }
        for r in rows
    ]


def delete_session(token: str):
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def log_event(token: str, event: str):
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO logs (token, event, ts) VALUES (?, ?, ?)",
        (token, event, time.time()),
    )
    conn.commit()
    conn.close()


def get_logs(limit=100) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT id, token, event, ts FROM logs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "token": r[1], "event": r[2], "ts": r[3]} for r in rows]
