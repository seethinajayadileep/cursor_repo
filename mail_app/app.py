from __future__ import annotations

import asyncio
import hmac
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from mail_app import auth, graph, store
from mail_app.config import load_settings
from mail_app.sanitize import sanitize_html
from mail_app.translate import TRANSLATE_LANGS, TranslateError, translate_pair

ROOT = Path(__file__).resolve().parent
settings = load_settings()
FOLDERS = (
    ("inbox", "Inbox", "IN"),
    ("other", "Other", "OT"),
    ("sentitems", "Sent", "SN"),
    ("drafts", "Drafts", "DR"),
    ("junkemail", "Junk", "JK"),
    ("deleteditems", "Deleted", "DL"),
)
TOKEN_TTL_SECONDS = 20 * 60
FEED_TTL_SECONDS = 20
FEED_CAP = 400
IST = ZoneInfo("Asia/Kolkata")
_token_cache: dict[str, tuple[float, str]] = {}
_feed_cache: dict[tuple, tuple[float, tuple]] = {}

async def keep_connected_accounts() -> int:
    """Refresh stored Microsoft tokens so mailboxes stay linked until revoked."""
    if not settings.session_secret:
        return 0
    refs = store.list_mailbox_refs()

    async def one(ref: store.MailboxRef) -> bool:
        try:
            account = store.get_account(ref.id, settings.session_secret)
        except RuntimeError:
            return False
        if not account:
            return False
        _token_cache.pop(account.id, None)
        return bool(await _token_for_account(account))

    results = await asyncio.gather(*(one(ref) for ref in refs))
    return sum(1 for ok in results if ok)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    try:
        store.backup_database()
    except Exception:
        pass
    task = None
    disabled = os.getenv("DISABLE_TOKEN_KEEPALIVE", "").lower() in {"1", "true", "yes"}
    if not disabled:

        async def _loop() -> None:
            wait = int(os.getenv("TOKEN_KEEPALIVE_SECONDS", str(6 * 60 * 60)))
            wait = max(wait, 60)
            while True:
                try:
                    await keep_connected_accounts()
                except Exception:
                    pass
                await asyncio.sleep(wait)

        task = asyncio.create_task(_loop())
    yield
    if task:
        task.cancel()


app = FastAPI(title="Host Inbox", docs_url=None, redoc_url=None, lifespan=_lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret or "dev-only-change-me",
    session_cookie="outlook_inbox_session",
    same_site="lax",
    https_only=settings.https_only,
    max_age=60 * 60 * 24 * 400,
)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def _session_user(request: Request) -> dict | None:
    user = request.session.get("user")
    if not user or not request.session.get("host"):
        return None
    return user


def _owner_email(request: Request) -> str | None:
    email = request.session.get("owner_email")
    return email.lower() if email else None


def _can_open(request: Request, account: store.Account) -> bool:
    owner = _owner_email(request)
    user = _session_user(request)
    if not owner or not user:
        return False
    return account.owner_email == owner or account.email == (user.get("email") or "").lower()


def _admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "").strip()


def _admin_password_ok(password: str) -> bool:
    expected = _admin_password()
    if not expected:
        return False
    return hmac.compare_digest((password or "").encode("utf-8"), expected.encode("utf-8"))


def _admin_session(request: Request) -> bool:
    return bool(request.session.get("admin"))


def _admin_mailboxes(request: Request) -> list[store.MailboxRef] | None:
    expected = _admin_password()
    if expected:
        if _admin_session(request):
            return store.list_mailbox_refs()
        return None
    owner = _owner_email(request)
    if _session_user(request) and owner:
        return store.list_mailbox_refs(owner)
    return None


@dataclass
class UnifiedItem:
    account_id: str
    mailbox: str
    message_id: str
    sender: str
    initials: str
    subject: str
    preview: str
    when: str
    received: str
    is_read: bool
    folder: str


async def collect_linked_inbox(
    refs: list[store.MailboxRef],
    *,
    box_id: str = "",
    query: str = "",
    per_box: int = 20,
) -> tuple[list[UnifiedItem], list[str], int]:
    chosen = [ref for ref in refs if not box_id or ref.id == box_id]
    needle = query.strip()
    cache_key = (box_id, tuple(ref.id for ref in chosen), per_box, needle.lower())
    cached = _feed_cache.get(cache_key)
    now = time.monotonic()
    if cached and cached[0] > now:
        items, skipped, incoming_total = cached[1]
        return list(items), list(skipped), incoming_total

    skipped: list[str] = []
    items: list[UnifiedItem] = []
    incoming_total = 0

    def rows_from(ref: store.MailboxRef, messages: list[dict]) -> list[UnifiedItem]:
        rows: list[UnifiedItem] = []
        for message in messages:
            received = message.get("receivedDateTime") or ""
            folder = message.get("_incoming_folder") or "inbox"
            rows.append(
                UnifiedItem(
                    account_id=ref.id,
                    mailbox=ref.email,
                    message_id=message.get("id") or "",
                    sender=sender_name(message),
                    initials=sender_initials(message),
                    subject=message.get("subject") or "",
                    preview=message.get("bodyPreview") or "",
                    when=_format_when(received),
                    received=received,
                    is_read=bool(message.get("isRead")),
                    folder=folder,
                )
            )
        return rows

    async def one(ref: store.MailboxRef) -> tuple[list[UnifiedItem], str | None, int]:
        try:
            account = store.get_account(ref.id, settings.session_secret)
        except Exception:
            return [], ref.email, 0
        if not account:
            return [], ref.email, 0
        token = await _token_for_account(account)
        if not token:
            return [], ref.email, 0

        async def load_messages() -> list[dict]:
            if needle:
                try:
                    found = await graph.search_messages(token, needle, top=per_box)
                except Exception:
                    found = await graph.list_incoming_messages(token, top_per_folder=per_box)
                    q = needle.lower()
                    found = [
                        message
                        for message in found
                        if q
                        in " ".join(
                            [
                                str(message.get("subject") or ""),
                                str(message.get("bodyPreview") or ""),
                                sender_name(message),
                                sender_email(message),
                            ]
                        ).lower()
                    ]
                for message in found:
                    message["_incoming_folder"] = message.get("_incoming_folder") or "inbox"
                return found
            return await graph.list_incoming_messages(token, top_per_folder=per_box)

        async def load_total() -> int:
            try:
                counts = await graph.folder_counts(token)
            except Exception:
                return 0
            return int(counts.get("inbox", {}).get("total") or 0) + int(
                counts.get("junkemail", {}).get("total") or 0
            )

        try:
            messages, total = await asyncio.wait_for(
                asyncio.gather(load_messages(), load_total()),
                timeout=12,
            )
        except (graph.GraphError, TimeoutError):
            return [], ref.email, 0
        return rows_from(ref, messages), None, total

    results = await asyncio.gather(*(one(ref) for ref in chosen), return_exceptions=True)
    for ref, result in zip(chosen, results):
        if isinstance(result, Exception):
            skipped.append(ref.email)
            continue
        rows, err, total = result
        items.extend(rows)
        incoming_total += total
        if err:
            skipped.append(err)
    items.sort(key=lambda item: graph.parse_graph_time(item.received), reverse=True)
    items = items[:FEED_CAP]
    _feed_cache[cache_key] = (
        time.monotonic() + FEED_TTL_SECONDS,
        (list(items), list(skipped), incoming_total),
    )
    return items, skipped, incoming_total


async def _token_for_account(account: store.Account) -> str | None:
    cached = _token_cache.get(account.id)
    now = time.monotonic()
    if cached and cached[0] > now:
        return cached[1]
    result = await asyncio.to_thread(
        auth.refresh_access_token, settings, account.refresh_token
    )
    if not result:
        return None
    if result.get("refresh_token"):
        store.update_refresh(account.id, result["refresh_token"], settings.session_secret)
    token = result["access_token"]
    _token_cache[account.id] = (now + TOKEN_TTL_SECONDS, token)
    return token


async def _access_token(request: Request) -> str | None:
    token = request.session.get("access_token")
    if token:
        return token
    refresh = request.session.get("refresh_token")
    if not refresh or not settings.configured:
        return None
    result = await asyncio.to_thread(auth.refresh_access_token, settings, refresh)
    if not result:
        return None
    request.session["access_token"] = result["access_token"]
    if result.get("refresh_token"):
        request.session["refresh_token"] = result["refresh_token"]
    return result["access_token"]


def _to_ist(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def _format_when(value: str | None) -> str:
    dt = _to_ist(value)
    if not dt:
        return value or ""
    return dt.strftime("%d %b · %H:%M IST")


def _format_when_short(value: str | None) -> str:
    dt = _to_ist(value)
    if not dt:
        return value or ""
    if dt.date() == datetime.now(IST).date():
        return dt.strftime("%H:%M")
    return dt.strftime("%d %b")


def sender_name(message: dict) -> str:
    from_ = (message.get("from") or {}).get("emailAddress") or {}
    return from_.get("name") or from_.get("address") or "(unknown)"


def sender_email(message: dict) -> str:
    from_ = (message.get("from") or {}).get("emailAddress") or {}
    return from_.get("address") or ""


def sender_initials(message: dict) -> str:
    name = sender_name(message)
    parts = [p for p in name.replace("(", " ").split() if p.isalpha() or p[:1].isalpha()]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()


def recipient_line(message: dict, field: str = "toRecipients") -> str:
    names: list[str] = []
    for person in message.get(field) or []:
        addr = person.get("emailAddress") or {}
        names.append(addr.get("name") or addr.get("address") or "")
    return ", ".join(name for name in names if name)


def folder_label(folder: str) -> str:
    for key, label, _tag in FOLDERS:
        if key == folder:
            return label
    return "Inbox"


def account_url(account_id: str) -> str:
    return f"{settings.public_base_url}/a/{account_id}"


def mail_href(account_id: str, message: dict, folder: str) -> str:
    mid = quote(message.get("id") or "", safe="")
    return f"/a/{account_id}?folder={folder}&msg={mid}"


templates.env.filters["when"] = _format_when
templates.env.filters["when_short"] = _format_when_short
templates.env.globals["sender_name"] = sender_name
templates.env.globals["sender_email"] = sender_email
templates.env.globals["sender_initials"] = sender_initials
templates.env.globals["recipient_line"] = recipient_line
templates.env.globals["folder_label"] = folder_label
templates.env.globals["account_url"] = account_url
templates.env.globals["mail_href"] = mail_href
templates.env.globals["public_base_url"] = settings.public_base_url
def translator_is_azure() -> bool:
    return bool(os.getenv("AZURE_TRANSLATOR_KEY", "").strip())


templates.env.globals["translate_langs"] = TRANSLATE_LANGS
templates.env.globals["translator_is_azure"] = translator_is_azure


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/healthz")
async def healthz():
    keepalive = os.getenv("DISABLE_TOKEN_KEEPALIVE", "").lower() not in {"1", "true", "yes"}
    return JSONResponse({"ok": True, "keepalive": keepalive})


@app.get("/robots.txt")
async def robots():
    return Response("User-agent: *\nDisallow: /\n", media_type="text/plain")


@app.get("/.well-known/microsoft-identity-association.json")
async def microsoft_identity_association():
    path = ROOT / "static" / ".well-known" / "microsoft-identity-association.json"
    return Response(
        path.read_text(encoding="utf-8"),
        media_type="application/json",
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if _session_user(request) and request.session.get("active_account_id"):
        return RedirectResponse(
            f"/a/{request.session['active_account_id']}", status_code=302
        )
    return templates.TemplateResponse(
        request,
        "login.html",
        {"configured": settings.configured},
    )


@app.get("/login")
async def login(request: Request):
    if not settings.configured:
        return RedirectResponse("/?error=not_configured", status_code=302)
    flow = auth.start_login(settings)
    request.session["auth_flow"] = flow
    state = flow.get("state")
    if state:
        store.save_flow(str(state), flow, settings.session_secret)
    return RedirectResponse(flow["auth_uri"], status_code=302)


@app.api_route("/auth/callback", methods=["GET", "POST"])
async def callback(request: Request):
    if request.method == "POST":
        params = dict(await request.form())
    else:
        params = dict(request.query_params)
    if params.get("error"):
        return RedirectResponse("/?error=microsoft", status_code=302)
    state = str(params.get("state") or "")
    flow = request.session.pop("auth_flow", None)
    if not flow:
        flow = store.pop_flow(state, settings.session_secret)
    if not flow:
        return RedirectResponse("/?error=session", status_code=302)
    try:
        result = auth.finish_login(settings, flow, params)
    except Exception:
        return RedirectResponse("/?error=login", status_code=302)

    request.session["access_token"] = result["access_token"]
    if result.get("refresh_token"):
        request.session["refresh_token"] = result["refresh_token"]

    me = await graph.get_me(result["access_token"])
    email = (me.get("mail") or me.get("userPrincipalName") or "").lower()
    name = me.get("displayName") or email
    owner = _owner_email(request) or email
    request.session["host"] = True
    request.session["owner_email"] = owner
    request.session["user"] = {"name": name, "email": email}

    if result.get("refresh_token"):
        account = store.upsert_account(
            secret=settings.session_secret,
            owner_email=owner,
            email=email,
            name=name,
            refresh_token=result["refresh_token"],
        )
        request.session["active_account_id"] = account.id
        return RedirectResponse(f"/a/{account.id}", status_code=302)
    return RedirectResponse("/inbox", status_code=302)


@app.get("/logout")
async def logout():
    return RedirectResponse("/", status_code=302)


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if not _admin_password():
        return RedirectResponse("/", status_code=302)
    if _admin_session(request):
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {"error": False},
    )


@app.post("/admin/login")
async def admin_login(request: Request, password: str = Form("")):
    expected = _admin_password()
    if not expected:
        return RedirectResponse("/", status_code=302)
    if not _admin_password_ok(password):
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {"error": True},
            status_code=401,
        )
    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/signout")
async def admin_signout(request: Request, password: str = Form("")):
    if not _admin_session(request) or not _admin_password():
        return RedirectResponse("/admin/login" if _admin_password() else "/", status_code=302)
    if not _admin_password_ok(password):
        mailboxes = _admin_mailboxes(request) or []
        return templates.TemplateResponse(
            request,
            "admin.html",
            {
                "mailboxes": mailboxes,
                "full_directory": True,
                "password_login": True,
                "signout_error": True,
                "admin_page": "directory",
            },
            status_code=401,
        )
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)


@app.get("/admin", response_class=HTMLResponse)
async def admin_directory(request: Request):
    mailboxes = _admin_mailboxes(request)
    if mailboxes is None:
        if _admin_password():
            return RedirectResponse("/admin/login", status_code=302)
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "mailboxes": mailboxes,
            "full_directory": bool(_admin_session(request)),
            "password_login": bool(_admin_password()),
            "signout_error": False,
            "admin_page": "directory",
        },
    )


@app.get("/admin/inbox", response_class=HTMLResponse)
async def admin_all_mail(request: Request):
    mailboxes = _admin_mailboxes(request)
    if mailboxes is None:
        if _admin_password():
            return RedirectResponse("/admin/login", status_code=302)
        return RedirectResponse("/", status_code=302)
    box_id = (request.query_params.get("box") or "").strip()
    query = request.query_params.get("q") or ""
    msg_id = (request.query_params.get("msg") or "").strip()
    open_account = (request.query_params.get("account") or "").strip()
    items, skipped, incoming_total = await collect_linked_inbox(mailboxes, box_id=box_id, query=query)
    return templates.TemplateResponse(
        request,
        "admin_inbox.html",
        {
            "mailboxes": mailboxes,
            "items": items,
            "skipped": skipped,
            "incoming_total": incoming_total,
            "q": query,
            "box_id": box_id,
            "msg_id": msg_id,
            "open_account": open_account,
            "full_directory": bool(_admin_session(request)),
            "password_login": bool(_admin_password()),
            "admin_page": "allmail",
        },
    )


@app.get("/admin/inbox/message")
async def admin_open_message(request: Request):
    mailboxes = _admin_mailboxes(request)
    if mailboxes is None:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    box_id = (request.query_params.get("box") or "").strip()
    msg_id = (request.query_params.get("msg") or "").strip()
    folder = (request.query_params.get("folder") or "inbox").strip() or "inbox"
    if not box_id or not msg_id:
        return JSONResponse({"error": "Missing message"}, status_code=400)
    if not any(ref.id == box_id for ref in mailboxes):
        return JSONResponse({"error": "Unknown mailbox"}, status_code=404)
    try:
        account = store.get_account(box_id, settings.session_secret)
    except RuntimeError:
        return JSONResponse({"error": "Mailbox locked"}, status_code=503)
    if not account:
        return JSONResponse({"error": "Unknown mailbox"}, status_code=404)
    token = await _token_for_account(account)
    if not token:
        return JSONResponse({"error": "Could not open mailbox"}, status_code=502)
    try:
        message = await graph.get_message(token, msg_id)
    except graph.GraphError:
        return JSONResponse({"error": "Could not open that message"}, status_code=502)
    body = (message.get("body") or {}).get("content") or ""
    if (message.get("body") or {}).get("contentType") == "html":
        body_html = sanitize_html(body)
    else:
        body_html = sanitize_html(f"<pre>{body}</pre>")
    if message.get("isRead") is False:
        try:
            await graph.set_read(token, msg_id, True)
            message["isRead"] = True
        except graph.GraphError:
            pass
    return JSONResponse(
        {
            "account_id": account.id,
            "mailbox": account.email,
            "folder": folder,
            "folder_label": folder_label(folder),
            "message_id": message.get("id") or msg_id,
            "subject": message.get("subject") or "(no subject)",
            "sender": sender_name(message),
            "sender_email": sender_email(message),
            "initials": sender_initials(message),
            "to": recipient_line(message),
            "cc": recipient_line(message, "ccRecipients"),
            "when": _format_when(message.get("receivedDateTime")),
            "body_html": body_html,
            "is_read": bool(message.get("isRead")),
        }
    )


@app.get("/inbox")
async def inbox_redirect(request: Request):
    account_id = request.session.get("active_account_id")
    if account_id:
        return RedirectResponse(f"/a/{account_id}", status_code=302)
    return RedirectResponse("/", status_code=302)


@app.post("/a/{account_id}/disconnect")
async def disconnect(request: Request, account_id: str, password: str = Form("")):
    if not _admin_session(request) or not _admin_password_ok(password):
        if _admin_password():
            return RedirectResponse("/admin/login", status_code=302)
        return RedirectResponse("/", status_code=302)
    account = store.get_mailbox_ref(account_id)
    if not account:
        return RedirectResponse("/admin", status_code=302)
    store.delete_account(account_id, account.owner_email)
    if request.session.get("active_account_id") == account_id:
        request.session.pop("active_account_id", None)
    return RedirectResponse("/admin", status_code=302)


async def _mailbox_token(request: Request, account_id: str) -> tuple[store.Account, str] | None:
    try:
        account = store.get_account(account_id, settings.session_secret)
    except RuntimeError:
        return None
    if not account:
        return None
    token = await _token_for_account(account)
    if not token:
        signed_in = bool(_session_user(request) and _can_open(request, account))
        if signed_in:
            token = await _access_token(request)
    if not token:
        return None
    return account, token


def _back_to_mailbox(account_id: str, folder: str, msg: str = "") -> RedirectResponse:
    url = f"/a/{account_id}?folder={quote(folder, safe='')}"
    if msg:
        url += f"&msg={quote(msg, safe='')}"
    return RedirectResponse(url, status_code=302)


@app.post("/a/{account_id}/translate")
async def translate_open_message(account_id: str, request: Request):
    if store.get_mailbox_ref(account_id) is None:
        return JSONResponse({"error": "Unknown mailbox"}, status_code=404)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    target = str(payload.get("target") or "").strip()
    subject = str(payload.get("subject") or "")
    body = str(payload.get("body") or "")
    try:
        translated_subject, translated_body = await translate_pair(subject, body, target)
    except TranslateError:
        return JSONResponse({"error": "Translation failed"}, status_code=502)
    return JSONResponse(
        {
            "subject": translated_subject,
            "body": translated_body,
            "target": target,
        }
    )


@app.post("/a/{account_id}/send")
async def send_message(
    request: Request,
    account_id: str,
    to: str = Form(""),
    subject: str = Form(""),
    body: str = Form(""),
    folder: str = Form("inbox"),
):
    loaded = await _mailbox_token(request, account_id)
    if not loaded:
        return RedirectResponse("/?error=auth", status_code=302)
    _account, token = loaded
    to_addr = (to or "").strip()
    if "@" not in to_addr:
        return _back_to_mailbox(account_id, folder)
    try:
        await graph.send_mail(token, to_addr, subject.strip() or "(no subject)", body)
    except graph.GraphError:
        return _back_to_mailbox(account_id, folder)
    return RedirectResponse(f"/a/{account_id}?folder=sentitems", status_code=302)


@app.post("/a/{account_id}/delete")
async def delete_open_message(
    request: Request,
    account_id: str,
    message_id: str = Form(""),
    folder: str = Form("inbox"),
):
    loaded = await _mailbox_token(request, account_id)
    if not loaded or not message_id:
        return RedirectResponse("/?error=auth", status_code=302)
    _account, token = loaded
    try:
        await graph.delete_message(token, message_id)
    except graph.GraphError:
        return _back_to_mailbox(account_id, folder, message_id)
    return _back_to_mailbox(account_id, folder)


@app.post("/a/{account_id}/read")
async def toggle_read(
    request: Request,
    account_id: str,
    message_id: str = Form(""),
    is_read: str = Form("true"),
    folder: str = Form("inbox"),
):
    loaded = await _mailbox_token(request, account_id)
    if not loaded or not message_id:
        return RedirectResponse("/?error=auth", status_code=302)
    _account, token = loaded
    try:
        await graph.set_read(token, message_id, is_read.lower() != "false")
    except graph.GraphError:
        pass
    return _back_to_mailbox(account_id, folder, message_id)


def _load_saved_account(account_id: str) -> tuple[store.Account | None, bool]:
    try:
        return store.get_account(account_id, settings.session_secret), False
    except RuntimeError:
        return None, True


@app.get("/a/{account_id}", response_class=HTMLResponse)
async def account_inbox(request: Request, account_id: str):
    account, locked = _load_saved_account(account_id)
    if locked:
        return templates.TemplateResponse(
            request,
            "locked.html",
            {"account_id": account_id},
            status_code=503,
        )
    if not account:
        return RedirectResponse("/", status_code=302)

    signed_in = bool(_session_user(request) and _can_open(request, account))
    user = _session_user(request) or {"name": account.name, "email": account.email}

    folder = request.query_params.get("folder") or "inbox"
    allowed = {key for key, _label, _tag in FOLDERS}
    if folder not in allowed:
        folder = "inbox"
    msg_id = request.query_params.get("msg")

    token = await _token_for_account(account)
    if not token and signed_in:
        token = await _access_token(request)
    if not token:
        return RedirectResponse("/?error=auth", status_code=302)

    error = None
    messages: list[dict] = []
    message = None
    body_html = ""
    counts: dict[str, dict] = {}

    async def load_counts() -> dict:
        try:
            return await graph.folder_counts(token)
        except Exception:
            return {}

    async def load_messages() -> list[dict]:
        if folder == "other":
            return await graph.list_other_messages(token, top=100)
        return await graph.list_messages(token, folder, top=100)

    async def load_open() -> dict | None:
        if not msg_id:
            return None
        return await graph.get_message(token, msg_id)

    count_result, message_result, open_result = await asyncio.gather(
        load_counts(), load_messages(), load_open(), return_exceptions=True
    )
    if isinstance(count_result, dict):
        counts = count_result
    if isinstance(message_result, Exception):
        error = "Could not load this mailbox. Connect the account again."
    else:
        messages = message_result
        if folder == "inbox":
            other_rows = [item for item in messages if graph.is_other_section(item)]
            counts = dict(counts)
            counts["other"] = {
                "unread": sum(1 for item in other_rows if not item.get("isRead")),
                "total": len(other_rows),
            }
    if isinstance(open_result, dict):
        message = open_result
        body = (message.get("body") or {}).get("content") or ""
        if (message.get("body") or {}).get("contentType") == "html":
            body_html = sanitize_html(body)
        else:
            body_html = sanitize_html(f"<pre>{body}</pre>")
        if message.get("isRead") is False:
            try:
                await graph.set_read(token, msg_id, True)
                message["isRead"] = True
            except graph.GraphError:
                pass
    elif msg_id and isinstance(open_result, Exception):
        error = error or "Could not open that message."

    if signed_in:
        request.session["active_account_id"] = account.id
        accounts = store.list_accounts(
            _owner_email(request) or account.owner_email, settings.session_secret
        )
    else:
        accounts = [account]

    return templates.TemplateResponse(
        request,
        "shell.html",
        {
            "user": user,
            "account": account,
            "accounts": accounts,
            "signed_in": signed_in,
            "folders": FOLDERS,
            "folder": folder,
            "counts": counts,
            "unread_here": sum(1 for item in messages if not item.get("isRead")),
            "messages": messages,
            "list_cap": 100,
            "message": message,
            "msg_id": msg_id,
            "body_html": body_html,
            "error": error,
        },
    )


@app.get("/mail/{message_id:path}")
async def legacy_mail(request: Request, message_id: str):
    account_id = request.session.get("active_account_id")
    if not account_id:
        return RedirectResponse("/", status_code=302)
    return RedirectResponse(
        f"/a/{account_id}?msg={quote(message_id, safe='')}",
        status_code=302,
    )
