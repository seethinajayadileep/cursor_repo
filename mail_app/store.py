from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("MAIL_DB_PATH", str(ROOT / "data" / "accounts.sqlite")))


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
    conn.commit()
    return conn


@dataclass
class Account:
    id: str
    owner_email: str
    email: str
    name: str
    refresh_token: str
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
    token = _fernet(secret).encrypt(refresh_token.encode("utf-8")).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM accounts WHERE owner_email = ? AND email = ?",
            (owner_email, email),
        ).fetchone()
        account_id = row["id"] if row else secrets.token_urlsafe(16)
        conn.execute(
            """
            INSERT INTO accounts (id, owner_email, email, name, refresh_token, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(owner_email, email) DO UPDATE SET
                name = excluded.name,
                refresh_token = excluded.refresh_token
            """,
            (account_id, owner_email, email, name, token, now),
        )
        conn.commit()
        saved = conn.execute(
            "SELECT * FROM accounts WHERE owner_email = ? AND email = ?",
            (owner_email, email),
        ).fetchone()
    return _row_to_account(saved, secret)


def get_account(account_id: str, secret: str) -> Account | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not row:
        return None
    return _row_to_account(row, secret)


def list_accounts(owner_email: str, secret: str) -> list[Account]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE owner_email = ? ORDER BY email",
            (owner_email.lower(),),
        ).fetchall()
    return [_row_to_account(row, secret) for row in rows]


def update_refresh(account_id: str, refresh_token: str, secret: str) -> None:
    token = _fernet(secret).encrypt(refresh_token.encode("utf-8")).decode("ascii")
    with _connect() as conn:
        conn.execute(
            "UPDATE accounts SET refresh_token = ? WHERE id = ?",
            (token, account_id),
        )
        conn.commit()


def delete_account(account_id: str, owner_email: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM accounts WHERE id = ? AND owner_email = ?",
            (account_id, owner_email.lower()),
        )
        conn.commit()


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
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pending_flows (state, payload, created_at) VALUES (?, ?, ?)",
            (state, payload, now),
        )
        conn.commit()


def pop_flow(state: str, secret: str) -> dict | None:
    if not state:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM pending_flows WHERE state = ?", (state,)
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM pending_flows WHERE state = ?", (state,))
        conn.commit()
    try:
        raw = _fernet(secret).decrypt(row["payload"].encode("ascii"))
    except InvalidToken:
        return None
    return json.loads(raw.decode("utf-8"))
