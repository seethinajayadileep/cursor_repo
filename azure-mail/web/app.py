#!/usr/bin/env python3
"""Browser UI: connect Hostinger/GoDaddy/… then add a mailbox in one form."""
from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "vm", ROOT, Path("/usr/local/lib/azure-mail")):
    if extra.is_dir():
        sys.path.insert(0, str(extra))

from lib_brand import (  # noqa: E402
    PROVIDERS,
    azure_ready,
    connected_ids,
    load_domains,
    load_env,
    load_providers,
    lookup_dns,
    provision,
    save_domain,
    save_providers,
    verification_status,
    verify_acs,
    write_env,
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
app.secret_key = os.environ.get("WEB_SECRET") or secrets.token_hex(24)
PREFIX = os.environ.get("WEB_PREFIX", "/brands")
if PREFIX:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, PREFIX)
    app.config["APPLICATION_ROOT"] = PREFIX.rstrip("/") or "/brands"
    app.config["SESSION_COOKIE_PATH"] = PREFIX.rstrip("/") or "/brands"
JOBS: dict[str, dict] = {}


def env() -> dict[str, str]:
    return load_env()


def setup_done(e: dict[str, str] | None = None) -> bool:
    e = e or env()
    return bool(e.get("MAILCOW_API_KEY") and e.get("AZURE_CLIENT_ID") and e.get("AZURE_CLIENT_SECRET"))


def require_login():
    if not session.get("ok"):
        return redirect(url_for("login"))
    return None


@app.context_processor
def inject():
    e = env()
    store = load_providers()
    return {
        "setup_done": setup_done(e),
        "connected": connected_ids(store),
        "providers": PROVIDERS,
        "mail_host": e.get("MAIL_HOSTNAME") or "mail.seethinajayadileep.dev",
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    e = env()
    expected = e.get("WEB_ADMIN_PASSWORD") or e.get("MAILCOW_API_KEY") or ""
    if request.method == "POST":
        if expected and request.form.get("password") == expected:
            session["ok"] = True
            return redirect(url_for("home"))
        flash("Wrong password. Use WEB_ADMIN_PASSWORD from brand.env (or the Mailcow API key).")
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
    records = lookup_dns(e, domain) if domain else []
    if domain and records:
        prev = saved.get(domain) or {}
        prev.update({"domain": domain, "records": records})
        save_domain(prev)
    status = {}
    if domain and azure_ready(e):
        try:
            status = verification_status(e, domain)
        except RuntimeError:
            status = {}
    return render_template(
        "dns.html",
        domain=domain,
        records=records,
        azure_needed=bool(domain) and not azure_ready(e),
        status=status,
        saved=saved,
        mailbox=saved.get(domain) or {},
        verified=bool(status) and all(v == "Verified" for v in status.values()),
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
            ok = all(v == "Verified" for v in st.values())
            JOBS[job_id]["result"] = {
                "domain": domain,
                "email": saved.get("email") or f"{local}@{domain}",
                "password": saved.get("password") or "",
                "webmail": saved.get("webmail") or "",
                "records": lookup_dns(env(), domain),
                "verify_status": st,
                "verified": ok,
            }
            JOBS[job_id]["status"] = "ok" if ok else "error"
            if not ok:
                JOBS[job_id]["error"] = f"Not verified yet: {st}. Add the DNS rows, wait a few minutes, click Verify again."
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
    if not session.get("ok"):
        return {"error": "login"}, 401
    data = JOBS.get(job_id)
    if not data:
        return {"error": "missing"}, 404
    return {
        "status": data["status"],
        "log": data["log"],
        "result": data["result"],
        "error": data["error"],
    }


def main() -> None:
    host = os.environ.get("WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_PORT", "8787"))
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
