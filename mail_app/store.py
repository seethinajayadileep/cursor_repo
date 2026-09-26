from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ROOT = Path(__file__).resolve().parent


def db_path() -> Path:
    return Path(os.getenv("MAIL_DB_PATH", str(ROOT / "data" / "accounts.sqlite")))


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, typedef: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            owner_email TEXT NOT NULL,
            email TEXT NOT NULL,
            name TEXT,
            refresh_token TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(owner_email, email)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_flows (
            state TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_column(conn, "accounts", "updated_at", "TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS accounts_owner_email ON accounts(owner_email, email)"
    )


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    return conn


@contextmanager
def _db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def backup_database() -> Path | None:
    """Write a consistent copy beside the live database. Never deletes accounts."""
    path = db_path()
    if not path.exists() or path.stat().st_size == 0:
        return None
    dest = Path(str(path) + ".bak")
    previous = Path(str(path) + ".bak.1")
    if dest.exists():
        dest.replace(previous)
    source = _connect()
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
    except Exception:
        if previous.exists():
            previous.replace(dest)
        raise
    finally:
        source.close()
    return dest


@dataclass
class Account:
    id: str
    owner_email: str
    email: str
    name: str
    refresh_token: str
    created_at: str


@dataclass(frozen=True)
class MailboxRef:
    id: str
    owner_email: str
    email: str
    name: str
    created_at: str


def upsert_account(
    *,
    secret: str,
    owner_email: str,
    email: str,
    name: str,
    refresh_token: str,
) -> Account:
    owner_email = owner_email.lower()
    email = email.lower()
    if not refresh_token:
        raise ValueError("refusing to store an empty mailbox token")
    token = _fernet(secret).encrypt(refresh_token.encode("utf-8")).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with _db() as conn:
        row = conn.execute(
            "SELECT id, created_at FROM accounts WHERE owner_email = ? AND email = ?",
            (owner_email, email),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE accounts
                SET name = ?, refresh_token = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, token, now, row["id"]),
            )
        else:
            account_id = secrets.token_urlsafe(16)
            try:
                conn.execute(
                    """
                    INSERT INTO accounts (
                        id, owner_email, email, name, refresh_token, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (account_id, owner_email, email, name, token, now, now),
                )
            except sqlite3.IntegrityError:
                conn.execute(
                    """
                    UPDATE accounts
                    SET name = ?, refresh_token = ?, updated_at = ?
                    WHERE owner_email = ? AND email = ?
                    """,
                    (name, token, now, owner_email, email),
                )
        saved = conn.execute(
            "SELECT * FROM accounts WHERE owner_email = ? AND email = ?",
            (owner_email, email),
        ).fetchone()
    return _row_to_account(saved, secret)


def get_account(account_id: str, secret: str) -> Account | None:
    with _db() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not row:
        return None
    return _row_to_account(row, secret)


def list_accounts(owner_email: str, secret: str) -> list[Account]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE owner_email = ? ORDER BY email",
            (owner_email.lower(),),
        ).fetchall()
    accounts: list[Account] = []
    for row in rows:
        try:
            accounts.append(_row_to_account(row, secret))
        except RuntimeError:
            continue
    return accounts


def _ref_from_row(row: sqlite3.Row) -> MailboxRef:
    return MailboxRef(
        id=row["id"],
        owner_email=row["owner_email"],
        email=row["email"],
        name=row["name"] or row["email"],
        created_at=row["created_at"],
    )


def get_mailbox_ref(account_id: str) -> MailboxRef | None:
    with _db() as conn:
        row = conn.execute(
            """
            SELECT id, owner_email, email, name, created_at
            FROM accounts WHERE id = ?
            """,
            (account_id,),
        ).fetchone()
    if not row:
        return None
    return _ref_from_row(row)


def list_mailbox_refs(owner_email: str | None = None) -> list[MailboxRef]:
    with _db() as conn:
        if owner_email:
            rows = conn.execute(
                """
                SELECT id, owner_email, email, name, created_at
                FROM accounts WHERE owner_email = ? ORDER BY email
                """,
                (owner_email.lower(),),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, owner_email, email, name, created_at
                FROM accounts ORDER BY email
                """
            ).fetchall()
    return [_ref_from_row(row) for row in rows]


def update_refresh(account_id: str, refresh_token: str, secret: str) -> None:
    if not refresh_token:
        return
    token = _fernet(secret).encrypt(refresh_token.encode("utf-8")).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with _db() as conn:
        conn.execute(
            "UPDATE accounts SET refresh_token = ?, updated_at = ? WHERE id = ?",
            (token, now, account_id),
        )


def delete_account(account_id: str, owner_email: str) -> None:
    with _db() as conn:
        conn.execute(
            "DELETE FROM accounts WHERE id = ? AND owner_email = ?",
            (account_id, owner_email.lower()),
        )


def _row_to_account(row: sqlite3.Row, secret: str) -> Account:
    try:
        refresh = _fernet(secret).decrypt(row["refresh_token"].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Could not decrypt stored mailbox token") from exc
    return Account(
        id=row["id"],
        owner_email=row["owner_email"],
        email=row["email"],
        name=row["name"] or row["email"],
        refresh_token=refresh,
        created_at=row["created_at"],
    )


def save_flow(state: str, flow: dict, secret: str) -> None:
    payload = _fernet(secret).encrypt(json.dumps(flow).encode("utf-8")).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pending_flows (state, payload, created_at) VALUES (?, ?, ?)",
            (state, payload, now),
        )


def pop_flow(state: str, secret: str) -> dict | None:
    if not state:
        return None
    with _db() as conn:
        row = conn.execute(
            "SELECT payload FROM pending_flows WHERE state = ?", (state,)
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM pending_flows WHERE state = ?", (state,))
    try:
        raw = _fernet(secret).decrypt(row["payload"].encode("ascii"))
    except InvalidToken:
        return None
    return json.loads(raw.decode("utf-8"))
