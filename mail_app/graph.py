from __future__ import annotations

from urllib.parse import quote

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def graph_get(access_token: str, path: str, params: dict | None = None) -> dict:
    url = f"{GRAPH}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)
    if response.status_code >= 400:
        raise GraphError(response.status_code, response.text[:500])
    return response.json()


async def get_me(access_token: str) -> dict:
    return await graph_get(access_token, "/me")


async def list_messages(access_token: str, folder: str = "inbox", top: int = 80) -> list[dict]:
    data = await graph_get(
        access_token,
        f"/me/mailFolders/{folder}/messages",
        params={
            "$top": str(top),
            "$orderby": "receivedDateTime DESC",
            "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments",
        },
    )
    return data.get("value") or []


async def list_inbox(access_token: str, top: int = 50) -> list[dict]:
    return await list_messages(access_token, "inbox", top)


async def get_message(access_token: str, message_id: str) -> dict:
    encoded = quote(message_id, safe="")
    return await graph_get(
        access_token,
        f"/me/messages/{encoded}",
        params={"$select": "id,subject,from,toRecipients,receivedDateTime,body,isRead"},
    )
