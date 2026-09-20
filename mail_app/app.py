from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from mail_app import auth, graph
from mail_app.config import load_settings
from mail_app.sanitize import sanitize_html

ROOT = Path(__file__).resolve().parent
settings = load_settings()

app = FastAPI(title="Private Outlook Inbox")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret or "dev-only-change-me",
    session_cookie="outlook_inbox_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 8,
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def _session_user(request: Request) -> dict | None:
    user = request.session.get("user")
    token = request.session.get("access_token")
    if not user or not token:
        return None
    return user


async def _access_token(request: Request) -> str | None:
    token = request.session.get("access_token")
    if token:
        return token
    refresh = request.session.get("refresh_token")
    if not refresh or not settings.configured:
        return None
    result = auth.refresh_access_token(settings, refresh)
    if not result:
        request.session.clear()
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
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


templates.env.filters["when"] = _format_when


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if _session_user(request):
        return RedirectResponse("/inbox", status_code=302)
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
    return RedirectResponse(flow["auth_uri"], status_code=302)


@app.get("/auth/callback")
async def callback(request: Request):
    flow = request.session.pop("auth_flow", None)
    if not flow:
        return RedirectResponse("/?error=session", status_code=302)
    try:
        result = auth.finish_login(settings, flow, dict(request.query_params))
    except Exception:
        return RedirectResponse("/?error=login", status_code=302)

    request.session["access_token"] = result["access_token"]
    if result.get("refresh_token"):
        request.session["refresh_token"] = result["refresh_token"]

    me = await graph.get_me(result["access_token"])
    request.session["user"] = {
        "name": me.get("displayName") or me.get("userPrincipalName"),
        "email": me.get("mail") or me.get("userPrincipalName"),
    }
    return RedirectResponse("/inbox", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@app.get("/inbox", response_class=HTMLResponse)
async def inbox(request: Request):
    user = _session_user(request)
    token = await _access_token(request)
    if not user or not token:
        return RedirectResponse("/", status_code=302)
    try:
        messages = await graph.list_inbox(token)
    except graph.GraphError as exc:
        if exc.status_code in {401, 403}:
            request.session.clear()
            return RedirectResponse("/?error=auth", status_code=302)
        return templates.TemplateResponse(
            request,
            "inbox.html",
            {"user": user, "messages": [], "error": "Could not load inbox."},
            status_code=502,
        )
    return templates.TemplateResponse(
        request,
        "inbox.html",
        {"user": user, "messages": messages, "error": None},
    )


@app.get("/mail/{message_id:path}", response_class=HTMLResponse)
async def read_mail(request: Request, message_id: str):
    user = _session_user(request)
    token = await _access_token(request)
    if not user or not token:
        return RedirectResponse("/", status_code=302)
    try:
        message = await graph.get_message(token, message_id)
    except graph.GraphError as exc:
        if exc.status_code in {401, 403}:
            request.session.clear()
            return RedirectResponse("/?error=auth", status_code=302)
        return templates.TemplateResponse(
            request,
            "message.html",
            {"user": user, "message": None, "body_html": "", "error": "Message not found."},
            status_code=404,
        )
    body = (message.get("body") or {}).get("content") or ""
    if (message.get("body") or {}).get("contentType") == "html":
        body_html = sanitize_html(body)
    else:
        body_html = sanitize_html(f"<pre>{body}</pre>")
    return templates.TemplateResponse(
        request,
        "message.html",
        {
            "user": user,
            "message": message,
            "body_html": body_html,
            "error": None,
        },
    )


def sender_name(message: dict) -> str:
    from_ = (message.get("from") or {}).get("emailAddress") or {}
    return from_.get("name") or from_.get("address") or "(unknown)"


def mail_href(message: dict) -> str:
    return "/mail/" + quote(message.get("id") or "", safe="")


templates.env.globals["sender_name"] = sender_name
templates.env.globals["mail_href"] = mail_href
