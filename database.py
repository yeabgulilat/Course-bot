"""
Tiny PostgreSQL helper (Neon). One table: registrations.
Every status change is done with "UPDATE ... WHERE status = <expected>"
so the same payment can never be processed twice.
"""
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from config import DATABASE_URL


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect():
    # dict_row: rows behave like dictionaries, e.g. reg["status"]
    # prepare_threshold=None: avoids problems with Neon's connection pooler
    return psycopg.connect(
        DATABASE_URL, row_factory=dict_row, connect_timeout=15, prepare_threshold=None
    )


def _execute(sql, params=()):
    """Run a write statement. Returns the number of rows changed."""
    with _connect() as conn:  # commits automatically, then closes
        return conn.execute(sql, params).rowcount


def _fetchone(sql, params=()):
    with _connect() as conn:
        return conn.execute(sql, params).fetchone()


def init_db():
    _execute(
        """
        CREATE TABLE IF NOT EXISTS registrations (
            id            BIGSERIAL PRIMARY KEY,
            user_id       BIGINT NOT NULL,
            username      TEXT,
            package       TEXT NOT NULL,
            amount        INTEGER NOT NULL,
            status        TEXT NOT NULL,
            proof_file_id TEXT,
            proof_type    TEXT,
            invite_link   TEXT,
            decided_by    BIGINT,
            created_at    TEXT,
            updated_at    TEXT
        )
        """
    )


def create_registration(user_id, username, package, amount):
    """Start a new registration. Old unfinished ones for this user are cancelled."""
    now = _now()
    _execute(
        "UPDATE registrations SET status='cancelled', updated_at=%s "
        "WHERE user_id=%s AND status IN ('selected','awaiting_proof','rejected')",
        (now, user_id),
    )
    row = _fetchone(
        "INSERT INTO registrations (user_id, username, package, amount, status, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, 'selected', %s, %s) RETURNING id",
        (user_id, username, package, amount, now, now),
    )
    return row["id"]


def get_registration(reg_id):
    return _fetchone("SELECT * FROM registrations WHERE id=%s", (reg_id,))


def get_latest_for_user(user_id, statuses):
    """Newest registration of this user whose status is in the given list."""
    marks = ",".join("%s" for _ in statuses)
    return _fetchone(
        f"SELECT * FROM registrations WHERE user_id=%s AND status IN ({marks}) "
        "ORDER BY id DESC LIMIT 1",
        (user_id, *statuses),
    )


def find_by_invite_link(link):
    return _fetchone("SELECT * FROM registrations WHERE invite_link=%s", (link,))


def set_status_if(reg_id, from_status, to_status, decided_by=None, invite_link=None):
    """
    Change status ONLY if it is currently from_status.
    Returns True if the change happened, False if someone else already changed it.
    """
    changed = _execute(
        "UPDATE registrations SET status=%s, decided_by=COALESCE(%s::bigint, decided_by), "
        "invite_link=COALESCE(%s::text, invite_link), updated_at=%s WHERE id=%s AND status=%s",
        (to_status, decided_by, invite_link, _now(), reg_id, from_status),
    )
    return changed == 1


def save_proof(reg_id, file_id, file_type):
    """Store the screenshot and move to pending_review (only if allowed)."""
    changed = _execute(
        "UPDATE registrations SET proof_file_id=%s, proof_type=%s, status='pending_review', updated_at=%s "
        "WHERE id=%s AND status IN ('awaiting_proof','rejected')",
        (file_id, file_type, _now(), reg_id),
    )
    return changed == 1