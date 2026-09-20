from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from mail_app import auth, graph, store
from mail_app.config import load_settings
from mail_app.sanitize import sanitize_html

ROOT = Path(__file__).resolve().parent
settings = load_settings()
FOLDERS = (
    ("inbox", "Inbox", "IN"),
    ("sentitems", "Sent", "SN"),
    ("drafts", "Drafts", "DR"),
    ("junkemail", "Junk", "JK"),
    ("deleteditems", "Deleted", "DL"),
)

app = FastAPI(title="Host Inbox", docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret or "dev-only-change-me",
    session_cookie="outlook_inbox_session",
    same_site="lax",
    https_only=settings.https_only,
    max_age=60 * 60 * 24 * 30,
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


async def _token_for_account(account: store.Account) -> str | None:
    result = auth.refresh_access_token(settings, account.refresh_token)
    if not result:
        return None
    if result.get("refresh_token"):
        store.update_refresh(account.id, result["refresh_token"], settings.session_secret)
    return result["access_token"]


async def _access_token(request: Request) -> str | None:
    token = request.session.get("access_token")
    if token:
        return token
    refresh = request.session.get("refresh_token")
    if not refresh or not settings.configured:
        return None
    result = auth.refresh_access_token(settings, refresh)
    if not result:
        return None
    request.session["access_token"] = result["access_token"]
    if result.get("refresh_token"):
        request.session["refresh_token"] = result["refresh_token"]
    return result["access_token"]


def _format_when(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d %b · %H:%M")
    except ValueError:
        return value


def sender_name(message: dict) -> str:
    from_ = (message.get("from") or {}).get("emailAddress") or {}
    return from_.get("name") or from_.get("address") or "(unknown)"


def sender_initials(message: dict) -> str:
    name = sender_name(message)
    parts = [p for p in name.replace("(", " ").split() if p.isalpha() or p[:1].isalpha()]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()


def account_url(account_id: str) -> str:
    return f"{settings.public_base_url}/a/{account_id}"


def mail_href(account_id: str, message: dict, folder: str) -> str:
    mid = quote(message.get("id") or "", safe="")
    return f"/a/{account_id}?folder={folder}&msg={mid}"


templates.env.filters["when"] = _format_when
templates.env.globals["sender_name"] = sender_name
templates.env.globals["sender_initials"] = sender_initials
templates.env.globals["account_url"] = account_url
templates.env.globals["mail_href"] = mail_href
templates.env.globals["public_base_url"] = settings.public_base_url


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
    return JSONResponse({"ok": True})


@app.get("/robots.txt")
async def robots():
    return Response("User-agent: *\nDisallow: /\n", media_type="text/plain")


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
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@app.get("/inbox")
async def inbox_redirect(request: Request):
    account_id = request.session.get("active_account_id")
    if account_id:
        return RedirectResponse(f"/a/{account_id}", status_code=302)
    return RedirectResponse("/", status_code=302)


@app.post("/a/{account_id}/disconnect")
async def disconnect(request: Request, account_id: str):
    owner = _owner_email(request)
    if not _session_user(request) or not owner:
        return RedirectResponse("/", status_code=302)
    store.delete_account(account_id, owner)
    if request.session.get("active_account_id") == account_id:
        request.session.pop("active_account_id", None)
    return RedirectResponse("/", status_code=302)


@app.get("/a/{account_id}", response_class=HTMLResponse)
async def account_inbox(request: Request, account_id: str):
    account = store.get_account(account_id, settings.session_secret)
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
    try:
        messages = await graph.list_messages(token, folder)
        if msg_id:
            message = await graph.get_message(token, msg_id)
            body = (message.get("body") or {}).get("content") or ""
            if (message.get("body") or {}).get("contentType") == "html":
                body_html = sanitize_html(body)
            else:
                body_html = sanitize_html(f"<pre>{body}</pre>")
    except graph.GraphError:
        error = "Could not load this mailbox. Connect the account again."

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
            "messages": messages,
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
