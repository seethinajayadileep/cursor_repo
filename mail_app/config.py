from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    tenant_id: str
    redirect_uri: str
    session_secret: str
    public_base_url: str
    https_only: bool
    scopes: tuple[str, ...] = (
        "User.Read",
        "Mail.ReadWrite",
        "Mail.Send",
    )

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.session_secret)


def load_settings() -> Settings:
    public = os.getenv("PUBLIC_BASE_URL", "http://localhost:8001").rstrip("/")
    https_only = os.getenv("HTTPS_ONLY", "").lower() in {"1", "true", "yes"}
    if public.startswith("https://"):
        https_only = True
    redirect = os.getenv("REDIRECT_URI", f"{public}/auth/callback")
    return Settings(
        client_id=os.getenv("AZURE_CLIENT_ID", ""),
        client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
        tenant_id=os.getenv("AZURE_TENANT_ID", "common"),
        redirect_uri=redirect,
        session_secret=os.getenv("SESSION_SECRET", ""),
        public_base_url=public,
        https_only=https_only,
    )
