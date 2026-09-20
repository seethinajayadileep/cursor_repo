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
    scopes: tuple[str, ...] = (
        "User.Read",
        "Mail.Read",
        "offline_access",
    )

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.session_secret)


def load_settings() -> Settings:
    return Settings(
        client_id=os.getenv("AZURE_CLIENT_ID", ""),
        client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
        tenant_id=os.getenv("AZURE_TENANT_ID", "common"),
        redirect_uri=os.getenv(
            "REDIRECT_URI", "http://localhost:8001/auth/callback"
        ),
        session_secret=os.getenv("SESSION_SECRET", ""),
    )
