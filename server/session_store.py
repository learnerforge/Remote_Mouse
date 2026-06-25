import sqlite3
import time
import uuid
import json
import logging
from pathlib import Path

logger = logging.getLogger("touchmorph.session")

DB_PATH = Path(__file__).resolve().parent / "touchmorph.db"

STALE_SESSION_HOURS = 24
MAX_LOG_ROWS = 1000


def _get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def _init():
    conn = _get_conn()
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            token       TEXT,
            category    TEXT DEFAULT 'general',
            event       TEXT,
            detail      TEXT DEFAULT '',
            ip          TEXT DEFAULT '',
            device_name TEXT DEFAULT '',
            severity    TEXT DEFAULT 'info',
            ts          REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_token     ON audit_logs(token)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_category  ON audit_logs(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_severity  ON audit_logs(severity)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts        ON audit_logs(ts)")
    conn.commit()
    conn.close()


_init()


# ─── Sessions ─────────────────────────────────────────────────────────────

def create_session(device_name="", ip="") -> str:
    token = str(uuid.uuid4())
    now = time.time()
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO sessions (token, device_name, ip, paired, mode, last_active, created) VALUES (?, ?, ?, 0, 'mouse', ?, ?)",
        (token, device_name, ip, now, now),
    )
    conn.commit()
    conn.close()
    return token


def restore_session(token: str) -> dict | None:
    conn = _get_conn()
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
    conn = _get_conn()
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
    conn = _get_conn()
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
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ─── Old Logs (backward compat) ───────────────────────────────────────────

def log_event(token: str, event: str):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO logs (token, event, ts) VALUES (?, ?, ?)",
        (token, event, time.time()),
    )
    conn.commit()
    conn.close()


def get_logs(limit=50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, token, event, ts FROM logs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "token": r[1], "event": r[2], "ts": r[3]} for r in rows]


# ─── Audit Logs ───────────────────────────────────────────────────────────

CATEGORIES = ("connection", "mouse", "touchpad", "airmouse", "presentation",
              "media", "system", "gesture", "admin", "security", "general")
SEVERITIES = ("info", "warning", "error")


def audit_log(token="", category="general", event="", detail="",
              ip="", device_name="", severity="info"):
    if category not in CATEGORIES:
        category = "general"
    if severity not in SEVERITIES:
        severity = "info"
    if isinstance(detail, dict):
        detail = json.dumps(detail, default=str)
    conn = _get_conn()
    conn.execute(
        "INSERT INTO audit_logs (token, category, event, detail, ip, device_name, severity, ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (token, category, event, str(detail), ip, device_name, severity, time.time()),
    )
    conn.commit()
    conn.close()
    # Also write to the legacy table for backward compatibility
    if event and token:
        log_event(token, f"{category}:{event}" if category != "general" else event)


def query_audit_logs(token=None, category=None, severity=None, search=None,
                     limit=50, offset=0, since=None, until=None) -> list[dict]:
    conn = _get_conn()
    where = []
    params = []
    if token:
        where.append("token = ?")
        params.append(token)
    if category:
        where.append("category = ?")
        params.append(category)
    if severity:
        where.append("severity = ?")
        params.append(severity)
    if since:
        where.append("ts >= ?")
        params.append(since)
    if until:
        where.append("ts <= ?")
        params.append(until)
    if search:
        where.append("(event LIKE ? OR detail LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    rows = conn.execute(
        f"SELECT id, token, category, event, detail, ip, device_name, severity, ts "
        f"FROM audit_logs {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "token": r[1], "category": r[2], "event": r[3],
            "detail": r[4], "ip": r[5], "device_name": r[6],
            "severity": r[7], "ts": r[8],
        }
        for r in rows
    ]


def count_audit_logs(token=None, category=None, severity=None, search=None,
                     since=None, until=None) -> int:
    conn = _get_conn()
    where = []
    params = []
    if token:
        where.append("token = ?")
        params.append(token)
    if category:
        where.append("category = ?")
        params.append(category)
    if severity:
        where.append("severity = ?")
        params.append(severity)
    if since:
        where.append("ts >= ?")
        params.append(since)
    if until:
        where.append("ts <= ?")
        params.append(until)
    if search:
        where.append("(event LIKE ? OR detail LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    count = conn.execute(
        f"SELECT COUNT(*) FROM audit_logs {where_sql}", params
    ).fetchone()[0]
    conn.close()
    return count


def get_audit_stats() -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    row = conn.execute("SELECT COUNT(DISTINCT token) FROM audit_logs").fetchone()
    unique_tokens = row[0] if row else 0
    rows = conn.execute(
        "SELECT category, COUNT(*) as c FROM audit_logs GROUP BY category ORDER BY c DESC"
    ).fetchall()
    by_category = {r[0]: r[1] for r in rows}
    today_start = int(time.time()) - 86400
    today = conn.execute(
        "SELECT COUNT(*) FROM audit_logs WHERE ts >= ?", (today_start,)
    ).fetchone()[0]
    severity_counts = {}
    for s in SEVERITIES:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE severity = ?", (s,)
        ).fetchone()[0]
        severity_counts[s] = cnt
    conn.close()
    return {
        "total": total,
        "unique_sessions": unique_tokens,
        "last_24h": today,
        "by_category": by_category,
        "by_severity": severity_counts,
    }


# ─── Cleanup ──────────────────────────────────────────────────────────────

def cleanup_stale_sessions(max_age_hours=STALE_SESSION_HOURS):
    cutoff = time.time() - max_age_hours * 3600
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE last_active < ?", (cutoff,))
    deleted = conn.total_changes
    conn.commit()
    conn.close()
    if deleted:
        logger.info(f"Cleaned {deleted} stale session(s)")
    return deleted


def trim_logs(max_rows=MAX_LOG_ROWS):
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    if count > max_rows:
        delete_count = count - max_rows
        conn.execute(
            "DELETE FROM logs WHERE id IN (SELECT id FROM logs ORDER BY id ASC LIMIT ?)",
            (delete_count,),
        )
        conn.commit()
        logger.info(f"Trimmed {delete_count} old log row(s)")
    conn.close()
    # Also trim audit_logs to a larger limit (10k)
    trim_audit_logs(max_rows * 10)
    return max(0, count - max_rows)


def trim_audit_logs(max_rows=MAX_LOG_ROWS * 10):
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    if count > max_rows:
        delete_count = count - max_rows
        conn.execute(
            "DELETE FROM audit_logs WHERE id IN (SELECT id FROM audit_logs ORDER BY id ASC LIMIT ?)",
            (delete_count,),
        )
        conn.commit()
        logger.info(f"Trimmed {delete_count} old audit log row(s)")
    conn.close()


def vacuum_db():
    conn = _get_conn()
    conn.execute("VACUUM")
    conn.close()
    logger.info("Database vacuumed")
