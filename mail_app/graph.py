from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"
_http: httpx.AsyncClient | None = None
_prefer_safe_select = False


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(
            timeout=12.0,
            limits=httpx.Limits(max_connections=60, max_keepalive_connections=30),
        )
    return _http


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
    headers: dict | None = None,
) -> dict:
    url = f"{GRAPH}{path}"
    request_headers = {"Authorization": f"Bearer {access_token}"}
    if headers:
        request_headers.update(headers)
    response = await _client().request(
        method, url, headers=request_headers, params=params, json=json
    )
    if response.status_code >= 400:
        raise GraphError(response.status_code, response.text[:500])
    if not response.content:
        return {}
    return response.json()


async def graph_get(
    access_token: str,
    path: str,
    params: dict | None = None,
    headers: dict | None = None,
) -> dict:
    return await graph_call("GET", access_token, path, params=params, headers=headers)


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


SAFE_SELECT = "id,subject,from,receivedDateTime,sentDateTime,bodyPreview,isRead,hasAttachments"
FULL_SELECT = SAFE_SELECT + ",inferenceClassification"


async def list_messages(access_token: str, folder: str = "inbox", top: int = 100) -> list[dict]:
    global _prefer_safe_select
    path = f"/me/mailFolders/{folder}/messages"
    attempts = [
        {"$top": str(top), "$orderby": "receivedDateTime desc", "$select": FULL_SELECT},
        {"$top": str(top), "$orderby": "receivedDateTime desc", "$select": SAFE_SELECT},
        {"$top": str(top), "$select": SAFE_SELECT},
    ]
    if _prefer_safe_select:
        attempts = attempts[1:]
    last_error: GraphError | None = None
    for params in attempts:
        try:
            data = await graph_get(access_token, path, params=params)
            return sort_newest_first(data.get("value") or [])
        except GraphError as exc:
            last_error = exc
            if exc.status_code == 400 and "inferenceClassification" in (params.get("$select") or ""):
                _prefer_safe_select = True
            if exc.status_code in {401, 403, 404}:
                raise
    if last_error:
        raise last_error
    return []


async def search_messages(access_token: str, query: str, top: int = 25) -> list[dict]:
    text = " ".join(query.replace('"', " ").split())
    if not text:
        return []
    data = await graph_get(
        access_token,
        "/me/messages",
        params={"$search": f'"{text}"', "$top": str(top), "$select": SAFE_SELECT},
        headers={"ConsistencyLevel": "eventual"},
    )
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


async def list_incoming_messages(access_token: str, top_per_folder: int = 20) -> list[dict]:
    seen: set[str] = set()
    incoming: list[dict] = []
    loaded_any = False
    auth_error: GraphError | None = None

    async def one_folder(folder: str) -> tuple[str, list[dict] | GraphError]:
        try:
            return folder, await list_messages(access_token, folder, top=top_per_folder)
        except GraphError as exc:
            return folder, exc

    loaded = await asyncio.gather(*(one_folder(folder) for folder in INCOMING_FOLDERS))
    for folder, batch in loaded:
        if isinstance(batch, GraphError):
            if batch.status_code in {401, 403}:
                auth_error = batch
            continue
        loaded_any = True
        for message in batch:
            mid = message.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            row = dict(message)
            row["_incoming_folder"] = incoming_section(message, folder)
            incoming.append(row)
    if auth_error and not loaded_any:
        raise auth_error
    return sort_newest_first(incoming)


_FOLDER_ALIASES = {
    "inbox": "inbox",
    "sentitems": "sentitems",
    "sent items": "sentitems",
    "drafts": "drafts",
    "junkemail": "junkemail",
    "junk email": "junkemail",
    "deleteditems": "deleteditems",
    "deleted items": "deleteditems",
}


def _folder_key(folder: dict) -> str:
    known = (folder.get("wellKnownName") or "").lower()
    name = (folder.get("displayName") or "").lower()
    return _FOLDER_ALIASES.get(known) or _FOLDER_ALIASES.get(name) or ""


def _count_pair(folder: dict) -> dict:
    return {
        "unread": int(folder.get("unreadItemCount") or 0),
        "total": int(folder.get("totalItemCount") or 0),
    }


async def _folder_list_counts(access_token: str) -> dict[str, dict]:
    mapped: dict[str, dict] = {}
    path = "/me/mailFolders"
    params: dict | None = {
        "$top": "100",
        "$select": "displayName,unreadItemCount,totalItemCount,wellKnownName",
    }
    for _ in range(10):
        try:
            data = await graph_get(access_token, path, params=params)
        except GraphError as exc:
            if (
                exc.status_code == 400
                and params
                and "wellKnownName" in str(params.get("$select") or "")
            ):
                params = {
                    "$top": "100",
                    "$select": "displayName,unreadItemCount,totalItemCount",
                }
                continue
            raise
        for folder in data.get("value") or []:
            key = _folder_key(folder)
            if key:
                mapped[key] = _count_pair(folder)
        next_link = str(data.get("@odata.nextLink") or "")
        if not next_link.startswith(GRAPH):
            break
        path = next_link[len(GRAPH) :]
        params = None
    return mapped


async def _well_known_count(access_token: str, folder: str) -> dict | None:
    try:
        data = await graph_get(
            access_token,
            f"/me/mailFolders/{folder}",
            params={"$select": "totalItemCount,unreadItemCount"},
        )
    except GraphError:
        return None
    return _count_pair(data)


async def inbox_and_junk_total(access_token: str) -> int:
    inbox, junk = await asyncio.gather(
        _well_known_count(access_token, "inbox"),
        _well_known_count(access_token, "junkemail"),
    )
    total = 0
    if isinstance(inbox, dict):
        total += inbox["total"]
    if isinstance(junk, dict):
        total += junk["total"]
    return total


async def folder_counts(access_token: str) -> dict[str, dict]:
    listed, inbox, junk = await asyncio.gather(
        _folder_list_counts(access_token),
        _well_known_count(access_token, "inbox"),
        _well_known_count(access_token, "junkemail"),
        return_exceptions=True,
    )
    mapped = listed if isinstance(listed, dict) else {}
    if isinstance(inbox, dict):
        mapped["inbox"] = inbox
    if isinstance(junk, dict):
        mapped["junkemail"] = junk
    if not mapped:
        raise GraphError(502, "could not read folder totals")
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
