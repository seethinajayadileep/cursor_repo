#!/usr/bin/env python3
"""Browser UI: connect Hostinger/GoDaddy/… then add a mailbox in one form."""
from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from pathlib import Path

from datetime import timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "web", ROOT / "vm", ROOT, Path("/usr/local/lib/azure-mail")):
    if extra.is_dir():
        sys.path.insert(0, str(extra))

from lib_brand import (  # noqa: E402
    PROVIDERS,
    azure_ready,
    can_link_domain,
    connected_ids,
    domain_linked,
    load_domains,
    load_env,
    load_providers,
    lookup_dns,
    mail_directory,
    mailbox_known,
    persist_sso_secret,
    provision,
    save_domain,
    save_providers,
    verification_status,
    verify_acs,
    webmail_sso_url,
    write_env,
)
from security import (  # noqa: E402
    PUBLIC_ENDPOINTS,
    SESSION_MAX_AGE,
    admin_password,
    clear_failures,
    client_ip,
    csrf_ok,
    csrf_token,
    establish_admin_session,
    locked_out,
    password_ok,
    persist_web_secret,
    record_failure,
    same_origin,
    session_valid,
)

class PrefixMiddleware:
    """Keep links under /brands/ when nginx strips that prefix."""

    def __init__(self, app, prefix: str):
        self.app = app
        self.prefix = prefix.rstrip("/") or "/brands"

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = self.prefix
        path = environ.get("PATH_INFO") or ""
        if path.startswith(self.prefix):
            environ["PATH_INFO"] = path[len(self.prefix) :] or "/"
        return self.app(environ, start_response)


app = Flask(__name__)
app.secret_key = persist_web_secret(write_env, load_env)
PREFIX = os.environ.get("WEB_PREFIX", "/brands")
if PREFIX:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, PREFIX)
    app.config["APPLICATION_ROOT"] = PREFIX.rstrip("/") or "/brands"
    app.config["SESSION_COOKIE_PATH"] = PREFIX.rstrip("/") or "/brands"
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_MAX_AGE),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.environ.get("WEB_COOKIE_SECURE", "1") not in ("0", "false"),
    SESSION_COOKIE_NAME="mailbox_admin",
)
JOBS: dict[str, dict] = {}


def env() -> dict[str, str]:
    return load_env()


def setup_done(e: dict[str, str] | None = None) -> bool:
    e = e or env()
    return bool(e.get("MAILCOW_API_KEY") and e.get("AZURE_CLIENT_ID") and e.get("AZURE_CLIENT_SECRET"))


def require_login():
    if not session_valid():
        session.clear()
        return redirect(url_for("login"))
    return None


@app.before_request
def enforce_admin_only():
    if request.endpoint in PUBLIC_ENDPOINTS or (request.endpoint or "").startswith("static"):
        return None
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if not app.config.get("TESTING") and not (same_origin(request) or csrf_ok(request)):
            flash("That submit was blocked. Refresh the page and try again.")
            target = request.endpoint if request.endpoint and request.endpoint != "login" else "home"
            try:
                return redirect(url_for(target))
            except Exception:  # noqa: BLE001
                return redirect(url_for("home"))
    if request.endpoint == "login":
        return None
    if not session_valid():
        session.clear()
        if request.endpoint == "job_json":
            return {"error": "login"}, 401
        return redirect(url_for("login"))
    return None


@app.after_request
def harden_headers(resp):
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; "
        "script-src 'self' 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'"
    )
    return resp


@app.context_processor
def inject():
    e = env()
    store = load_providers()
    return {
        "setup_done": setup_done(e),
        "connected": connected_ids(store),
        "providers": PROVIDERS,
        "mail_host": e.get("MAIL_HOSTNAME") or "mail.seethinajayadileep.dev",
        "csrf": csrf_token(),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if session_valid():
        return redirect(url_for("home"))
    e = env()
    expected = admin_password(e)
    ip = client_ip(request)
    if request.method == "POST":
        if locked_out(ip):
            flash("Too many failed sign-ins. Wait and try again.")
            return render_template("login.html", has_password=bool(expected)), 429
        given = request.form.get("password") or ""
        if password_ok(given, expected):
            clear_failures(ip)
            establish_admin_session()
            return redirect(url_for("home"))
        record_failure(ip)
        flash("Wrong admin password. Mailbox users sign in at webmail, not here.")
    return render_template("login.html", has_password=bool(expected))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def home():
    gate = require_login()
    if gate:
        return gate
    return render_template("home.html")


@app.route("/mailboxes")
def mailboxes():
    gate = require_login()
    if gate:
        return gate
    data = mail_directory(env())
    query = (request.args.get("q") or "").strip().lower()
    rows = data["domains"]
    if query:
        rows = [
            row
            for row in rows
            if query in row["domain"]
            or any(query in (box.get("email") or "").lower() for box in row["mailboxes"])
        ]
    return render_template(
        "mailboxes.html",
        domains=rows,
        domain_count=data["domain_count"],
        mailbox_count=data["mailbox_count"],
        shown_domains=len(rows),
        shown_mailboxes=sum(len(r["mailboxes"]) for r in rows),
        query=query,
        error=data.get("error"),
        webmail=data.get("webmail") or f"https://{env().get('MAIL_HOSTNAME') or 'mail.seethinajayadileep.dev'}/",
    )


@app.route("/mailboxes/webmail")
def open_webmail():
    gate = require_login()
    if gate:
        return gate
    email = (request.args.get("email") or "").strip().lower()
    if "@" not in email or "." not in email.split("@", 1)[1]:
        flash("Pick a mailbox first.")
        return redirect(url_for("mailboxes"))
    e = env()
    if not mailbox_known(e, email):
        flash(f"{email} is not a mailbox on this server.")
        return redirect(url_for("mailboxes"))
    persist_sso_secret(e)
    return redirect(webmail_sso_url(e, email))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    gate = require_login()
    if gate:
        return gate
    e = env()
    if request.method == "POST":
        pasted = (request.form.get("AZURE_SP_JSON") or "").strip()
        parsed = {}
        if pasted:
            try:
                raw = json.loads(pasted)
            except json.JSONDecodeError:
                flash("Azure JSON did not parse. Paste the whole Cloud Shell output.")
                return render_template("setup.html", e=e)
            parsed = {
                "AZURE_CLIENT_ID": str(raw.get("appId") or raw.get("clientId") or "").strip(),
                "AZURE_CLIENT_SECRET": str(raw.get("password") or raw.get("clientSecret") or "").strip(),
                "AZURE_TENANT_ID": str(raw.get("tenant") or raw.get("tenantId") or "").strip(),
            }
        write_env(
            {
                "AZURE_TENANT_ID": parsed.get("AZURE_TENANT_ID")
                or request.form.get("AZURE_TENANT_ID", "").strip(),
                "AZURE_CLIENT_ID": parsed.get("AZURE_CLIENT_ID")
                or request.form.get("AZURE_CLIENT_ID", "").strip(),
                "AZURE_CLIENT_SECRET": parsed.get("AZURE_CLIENT_SECRET")
                or request.form.get("AZURE_CLIENT_SECRET", "").strip()
                or e.get("AZURE_CLIENT_SECRET", ""),
                "AZURE_SUBSCRIPTION_ID": request.form.get("AZURE_SUBSCRIPTION_ID", "").strip(),
                "RESOURCE_GROUP": request.form.get("RESOURCE_GROUP", "").strip() or "mailboxRg",
                "ACS_NAME": request.form.get("ACS_NAME", "").strip() or "mailboxCs",
                "EMAIL_NAME": request.form.get("EMAIL_NAME", "").strip() or "mail-box",
                "MAILCOW_API_URL": request.form.get("MAILCOW_API_URL", "").strip(),
                "MAILCOW_API_KEY": request.form.get("MAILCOW_API_KEY", "").strip() or e.get("MAILCOW_API_KEY", ""),
                "MAIL_HOSTNAME": request.form.get("MAIL_HOSTNAME", "").strip(),
                "WEB_ADMIN_PASSWORD": request.form.get("WEB_ADMIN_PASSWORD", "").strip()
                or e.get("WEB_ADMIN_PASSWORD", ""),
            }
        )
        flash("Saved. Connect Hostinger / GoDaddy / others next.")
        return redirect(url_for("providers"))
    return render_template("setup.html", e=e)


@app.route("/providers", methods=["GET", "POST"])
def providers():
    gate = require_login()
    if gate:
        return gate
    store = load_providers()
    if request.method == "POST":
        pid = request.form.get("provider") or ""
        spec = next((p for p in PROVIDERS if p.id == pid), None)
        if spec:
            if request.form.get("disconnect"):
                store.pop(pid, None)
            else:
                prev = store.get(pid) or {}
                nxt = {}
                for key, _label, typ in spec.fields:
                    val = (request.form.get(key) or "").strip()
                    if not val and typ == "password":
                        val = str(prev.get(key) or "")
                    nxt[key] = val
                store[pid] = nxt
                if not all(store[pid].values()):
                    flash(f"Fill every {spec.name} field.")
                    if not prev:
                        store.pop(pid, None)
                    else:
                        store[pid] = prev
                    return redirect(url_for("providers"))
            save_providers(store)
            flash(f"{spec.name} {'disconnected' if request.form.get('disconnect') else 'connected'}.")
        return redirect(url_for("providers"))
    return render_template("providers.html", store=store)


@app.route("/add", methods=["GET", "POST"])
def add():
    gate = require_login()
    if gate:
        return gate
    if request.method == "POST":
        domain = (request.form.get("domain") or "").strip().lower()
        local = (request.form.get("local_part") or "hi").strip()
        password = (request.form.get("password") or "").strip()
        provider = request.form.get("provider") or "manual"
        if not domain or "." not in domain:
            flash("Enter a domain like shop.example or brand.com")
            return redirect(url_for("add"))
        job_id = uuid.uuid4().hex[:12]
        JOBS[job_id] = {"status": "running", "log": [], "result": None, "error": None}

        def run() -> None:
            def log(msg: str) -> None:
                JOBS[job_id]["log"].append(msg)

            try:
                result = provision(env(), domain, local, password, provider, log)
                JOBS[job_id]["result"] = result
                JOBS[job_id]["status"] = "ok"
            except Exception as exc:  # noqa: BLE001 — surface any provider/Azure error in the UI
                JOBS[job_id]["error"] = str(exc)
                JOBS[job_id]["status"] = "error"
                log(f"Error: {exc}")

        threading.Thread(target=run, daemon=True).start()
        return redirect(url_for("job", job_id=job_id))
    return render_template("add.html", connected=connected_ids())


@app.route("/dns")
def dns_page():
    gate = require_login()
    if gate:
        return gate
    e = env()
    domain = (request.args.get("domain") or "").strip().lower().rstrip(".")
    saved = load_domains()
    try:
        records = lookup_dns(e, domain) if domain else []
    except Exception:  # noqa: BLE001
        records = []
    if domain and records:
        prev = saved.get(domain) or {}
        prev.update({"domain": domain, "records": records})
        save_domain(prev)
    status = {}
    linked = False
    if domain and azure_ready(e):
        try:
            status = verification_status(e, domain)
        except Exception:  # noqa: BLE001 — Azure outage must not 500 the DNS page
            status = {}
        try:
            linked = domain_linked(e, domain)
        except Exception:  # noqa: BLE001
            linked = False
    send_ready = can_link_domain(status) and linked
    return render_template(
        "dns.html",
        domain=domain,
        records=records,
        azure_needed=bool(domain) and not azure_ready(e),
        status=status,
        saved=saved,
        mailbox=saved.get(domain) or {},
        verified=send_ready,
        send_ready=send_ready,
        linked=linked,
    )


@app.route("/dns/verify", methods=["POST"])
def dns_verify():
    gate = require_login()
    if gate:
        return gate
    domain = (request.form.get("domain") or "").strip().lower().rstrip(".")
    if not domain:
        flash("Enter a domain first.")
        return redirect(url_for("dns_page"))
    saved = load_domains().get(domain) or {}
    local = (request.form.get("local_part") or saved.get("local_part") or "hi").strip()
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"status": "running", "log": [], "result": None, "error": None, "kind": "verify"}

    def run() -> None:
        def log(msg: str) -> None:
            JOBS[job_id]["log"].append(msg)

        try:
            log(f"Checking DNS for {domain}…")
            st = verify_acs(env(), domain, [local], log)
            send_ok = can_link_domain(st)
            try:
                send_ok = send_ok and domain_linked(env(), domain)
            except RuntimeError:
                pass
            all_ok = all(v == "Verified" for v in st.values())
            JOBS[job_id]["result"] = {
                "domain": domain,
                "local_part": local,
                "email": saved.get("email") or f"{local}@{domain}",
                "password": saved.get("password") or "",
                "webmail": saved.get("webmail") or "",
                "records": lookup_dns(env(), domain),
                "verify_status": st,
                "verified": send_ok,
                "send_ready": send_ok,
            }
            JOBS[job_id]["status"] = "ok"
            prev = dict(saved)
            prev.update({"domain": domain, "local_part": local, "verify_status": st, "verified": send_ok})
            save_domain(prev)
            if not send_ok:
                pending = [k for k, v in st.items() if v != "Verified"]
                JOBS[job_id]["error"] = (
                    f"Do not send yet. Still pending: {', '.join(pending) or 'Domain'}. "
                    "Azure will not link mailboxCs until Domain, SPF, DKIM, and DKIM2 are Verified. "
                    "Gmail will bounce 501 until then. Click Verify again."
                )
            elif not all_ok:
                extra = [k for k, v in st.items() if v != "Verified"]
                log(f"Send is linked. Still finishing: {', '.join(extra)}")
        except Exception as exc:  # noqa: BLE001
            JOBS[job_id]["error"] = str(exc)
            JOBS[job_id]["status"] = "error"
            log(f"Error: {exc}")

    threading.Thread(target=run, daemon=True).start()
    return redirect(url_for("job", job_id=job_id))


@app.route("/job/<job_id>")
def job(job_id: str):
    gate = require_login()
    if gate:
        return gate
    data = JOBS.get(job_id)
    if not data:
        flash("That job expired. Start again.")
        return redirect(url_for("add"))
    return render_template("job.html", job_id=job_id, job=data)


@app.route("/job/<job_id>.json")
def job_json(job_id: str):
    if not session_valid():
        return {"error": "login"}, 401
    data = JOBS.get(job_id)
    if not data:
        return {"error": "missing"}, 404
    result = data["result"]
    if isinstance(result, dict):
        result = {k: v for k, v in result.items() if k != "password"}
    return {
        "status": data["status"],
        "log": data["log"],
        "result": result,
        "error": data["error"],
    }


def main() -> None:
    host = os.environ.get("WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_PORT", "8787"))
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
