from __future__ import annotations

from datetime import datetime, timezone
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


def parse_graph_time(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def message_sort_time(message: dict) -> datetime:
    for key in ("receivedDateTime", "sentDateTime", "createdDateTime"):
        if message.get(key):
            return parse_graph_time(str(message.get(key)))
    return parse_graph_time(None)


def sort_newest_first(messages: list[dict]) -> list[dict]:
    return sorted(messages, key=message_sort_time, reverse=True)


async def list_messages(access_token: str, folder: str = "inbox", top: int = 80) -> list[dict]:
    path = f"/me/mailFolders/{folder}/messages"
    params = {
        "$top": str(top),
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,sentDateTime,bodyPreview,isRead,hasAttachments,inferenceClassification",
    }
    try:
        data = await graph_get(access_token, path, params=params)
    except GraphError:
        params.pop("$orderby", None)
        data = await graph_get(access_token, path, params=params)
    return sort_newest_first(data.get("value") or [])


async def list_inbox(access_token: str, top: int = 50) -> list[dict]:
    return await list_messages(access_token, "inbox", top)


INCOMING_FOLDERS = ("inbox", "junkemail", "clutter")


def incoming_section(message: dict, folder: str) -> str:
    if folder == "junkemail":
        return "junkemail"
    if folder == "clutter":
        return "other"
    if str(message.get("inferenceClassification") or "").lower() == "other":
        return "other"
    return "inbox"


def is_other_section(message: dict) -> bool:
    return str(message.get("inferenceClassification") or "").lower() == "other"


async def list_other_messages(access_token: str, top: int = 80) -> list[dict]:
    inbox = await list_messages(access_token, "inbox", top)
    others = [message for message in inbox if is_other_section(message)]
    seen = {message.get("id") for message in others if message.get("id")}
    try:
        clutter = await list_messages(access_token, "clutter", top)
    except GraphError:
        clutter = []
    for message in clutter:
        mid = message.get("id")
        if mid and mid not in seen:
            others.append(message)
            seen.add(mid)
    return sort_newest_first(others)


async def list_incoming_messages(access_token: str, top_per_folder: int = 40) -> list[dict]:
    seen: set[str] = set()
    incoming: list[dict] = []
    for folder in INCOMING_FOLDERS:
        try:
            batch = await list_messages(access_token, folder, top=top_per_folder)
        except GraphError:
            continue
        for message in batch:
            mid = message.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            row = dict(message)
            row["_incoming_folder"] = incoming_section(message, folder)
            incoming.append(row)
    return sort_newest_first(incoming)


async def folder_counts(access_token: str) -> dict[str, dict]:
    data = await graph_get(
        access_token,
        "/me/mailFolders",
        params={
            "$top": "40",
            "$select": "displayName,unreadItemCount,totalItemCount,wellKnownName",
        },
    )
    aliases = {
        "inbox": "inbox",
        "sentitems": "sentitems",
        "sent items": "sentitems",
        "drafts": "drafts",
        "junkemail": "junkemail",
        "junk email": "junkemail",
        "deleteditems": "deleteditems",
        "deleted items": "deleteditems",
    }
    mapped: dict[str, dict] = {}
    for folder in data.get("value") or []:
        known = (folder.get("wellKnownName") or "").lower()
        name = (folder.get("displayName") or "").lower()
        key = aliases.get(known) or aliases.get(name)
        if not key:
            continue
        mapped[key] = {
            "unread": int(folder.get("unreadItemCount") or 0),
            "total": int(folder.get("totalItemCount") or 0),
        }
    return mapped


async def get_message(access_token: str, message_id: str) -> dict:
    encoded = quote(message_id, safe="")
    return await graph_get(
        access_token,
        f"/me/messages/{encoded}",
        params={
            "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,isRead,hasAttachments,bodyPreview"
        },
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
