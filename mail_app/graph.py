from __future__ import annotations

from urllib.parse import quote

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def graph_call(
    method: str,
    access_token: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    url = f"{GRAPH}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method, url, headers=headers, params=params, json=json
        )
    if response.status_code >= 400:
        raise GraphError(response.status_code, response.text[:500])
    if not response.content:
        return {}
    return response.json()


async def graph_get(access_token: str, path: str, params: dict | None = None) -> dict:
    return await graph_call("GET", access_token, path, params=params)


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


async def set_read(access_token: str, message_id: str, is_read: bool) -> None:
    encoded = quote(message_id, safe="")
    await graph_call(
        "PATCH",
        access_token,
        f"/me/messages/{encoded}",
        json={"isRead": is_read},
    )


async def delete_message(access_token: str, message_id: str) -> None:
    encoded = quote(message_id, safe="")
    await graph_call("DELETE", access_token, f"/me/messages/{encoded}")


async def send_mail(access_token: str, to: str, subject: str, body: str) -> None:
    await graph_call(
        "POST",
        access_token,
        "/me/sendMail",
        json={
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": True,
        },
    )
