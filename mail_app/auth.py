from __future__ import annotations

import msal

from mail_app.config import Settings


def confidential_app(settings: Settings) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        settings.client_id,
        authority=settings.authority,
        client_credential=settings.client_secret,
    )


def start_login(settings: Settings) -> dict:
    client = confidential_app(settings)
    return client.initiate_auth_code_flow(
        list(settings.scopes),
        redirect_uri=settings.redirect_uri,
    )


def finish_login(settings: Settings, flow: dict, query: dict) -> dict:
    client = confidential_app(settings)
    result = client.acquire_token_by_auth_code_flow(flow, query)
    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or "login failed"
        raise RuntimeError(str(error))
    return result


def refresh_access_token(settings: Settings, refresh_token: str) -> dict | None:
    client = confidential_app(settings)
    result = client.acquire_token_by_refresh_token(refresh_token, list(settings.scopes))
    if "access_token" not in result:
        # Keep the mailbox linked even if extra write scopes were added later.
        result = client.acquire_token_by_refresh_token(refresh_token, ["User.Read"])
    if "access_token" not in result:
        return None
    return result
