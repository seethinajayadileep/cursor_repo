"""Admin-panel access control. Mailbox logins never unlock this app."""
from __future__ import annotations

import hmac
import os
import secrets
import time
from collections import defaultdict
from urllib.parse import urlparse

from flask import Request, session

SESSION_MAX_AGE = int(os.environ.get("WEB_SESSION_MAX_AGE", "7200"))
FAIL_LIMIT = int(os.environ.get("WEB_LOGIN_FAIL_LIMIT", "5"))
FAIL_WINDOW = int(os.environ.get("WEB_LOGIN_FAIL_WINDOW", "900"))
PUBLIC_ENDPOINTS = frozenset({"login", "logout", "static"})

_fails: dict[str, list[float]] = defaultdict(list)


def admin_password(env: dict[str, str]) -> str:
    return (env.get("WEB_ADMIN_PASSWORD") or "").strip()


def password_ok(given: str | None, expected: str) -> bool:
    if not expected or not given:
        return False
    left = given.encode("utf-8")
    right = expected.encode("utf-8")
    if len(left) != len(right):
        hmac.compare_digest(right, right)
        return False
    return hmac.compare_digest(left, right)


def client_ip(req: Request) -> str:
    peer = (req.remote_addr or "").strip()
    forwarded = (req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded and peer.startswith("172.22."):
        return forwarded
    return peer or "unknown"


def locked_out(ip: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    recent = [t for t in _fails[ip] if now - t < FAIL_WINDOW]
    _fails[ip] = recent
    return len(recent) >= FAIL_LIMIT


def record_failure(ip: str) -> None:
    _fails[ip].append(time.time())


def clear_failures(ip: str) -> None:
    _fails.pop(ip, None)


def _request_hosts(req: Request) -> set[str]:
    hosts = set()
    for raw in (req.host, req.headers.get("X-Forwarded-Host") or ""):
        host = raw.split(",")[0].strip().split(":")[0].lower()
        if host:
            hosts.add(host)
    return hosts


def same_origin(req: Request) -> bool:
    """True when Origin/Referer match this host. Ignore null Origin (no-referrer)."""
    allowed = _request_hosts(req)
    if not allowed:
        return False
    for header in ("Origin", "Referer"):
        raw = (req.headers.get(header) or "").strip()
        if not raw or raw.lower() == "null":
            continue
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        if host:
            return host in allowed
    return False


def csrf_token() -> str:
    tok = (session.get("csrf") or "").strip()
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["csrf"] = tok
    return tok


def csrf_ok(req: Request) -> bool:
    given = (req.form.get("csrf") or req.headers.get("X-CSRF-Token") or "").strip()
    expected = (session.get("csrf") or "").strip()
    if not given or not expected:
        return False
    return hmac.compare_digest(given.encode(), expected.encode())


def session_valid() -> bool:
    if session.get("role") != "admin" or not session.get("ok"):
        return False
    started = float(session.get("auth_at") or 0)
    return started > 0 and (time.time() - started) <= SESSION_MAX_AGE


def establish_admin_session() -> None:
    session.clear()
    session["ok"] = True
    session["role"] = "admin"
    session["auth_at"] = time.time()
    session.permanent = True


def persist_web_secret(write_env, load_env) -> str:
    current = os.environ.get("WEB_SECRET") or (load_env().get("WEB_SECRET") or "").strip()
    if current:
        os.environ["WEB_SECRET"] = current
        return current
    current = secrets.token_hex(32)
    os.environ["WEB_SECRET"] = current
    try:
        write_env({"WEB_SECRET": current})
    except OSError:
        pass
    return current
