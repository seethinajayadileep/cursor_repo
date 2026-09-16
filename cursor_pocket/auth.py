"""Pairing PIN + session token. Anyone on Wi-Fi with the PIN can drive the laptop."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class Auth:
    pin: str
    max_attempts: int = 8
    tokens: set[str] = field(default_factory=set)
    failures: int = 0
    locked: bool = False

    @classmethod
    def generate(cls, pin: str | None = None) -> "Auth":
        if pin is None:
            pin = f"{secrets.randbelow(1_000_000):06d}"
        elif not (pin.isdigit() and len(pin) == 6):
            raise ValueError("PIN must be exactly 6 digits")
        return cls(pin=pin)

    def pair(self, pin: str) -> str:
        if self.locked:
            raise AuthError("Too many wrong PINs. Restart Cursor Pocket on the laptop.", 423)
        offered = "".join(ch for ch in (pin or "") if ch.isdigit())
        # compare_digest needs equal-length bytes; still require an exact 6-digit match.
        probe = offered if len(offered) == 6 else "000000"
        matched = hmac.compare_digest(probe, self.pin) and len(offered) == 6
        if not matched:
            self.failures += 1
            remaining = max(0, self.max_attempts - self.failures)
            if remaining == 0:
                self.locked = True
                raise AuthError("Too many wrong PINs. Restart Cursor Pocket on the laptop.", 423)
            raise AuthError(f"Wrong PIN. {remaining} tries left.")
        self.failures = 0
        token = secrets.token_urlsafe(32)
        self.tokens.add(token)
        return token

    def check(self, token: str | None) -> None:
        if not token or token not in self.tokens:
            raise AuthError("Pair this phone with the laptop PIN first.")

    def revoke(self, token: str) -> None:
        self.tokens.discard(token)


def extract_bearer(header: str | None, query_token: str | None = None) -> str | None:
    if header:
        prefix = "Bearer "
        if header.startswith(prefix):
            return header[len(prefix) :].strip() or None
    if query_token:
        return query_token.strip() or None
    return None


def fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:8]
