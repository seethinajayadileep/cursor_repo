#!/usr/bin/env python3
"""One command on the mail VM: Mailcow domain+mailbox + ACS verify/link/MailFrom.

  sudo add-brand example.com hi
  sudo add-brand example.com hi --password 'YourPass12'

Does not open the Azure portal. DNS is applied via Name.com if NAMECOM_* is set;
otherwise records are printed for you to paste once.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_PATH = Path(os.environ.get("AZURE_MAIL_ENV", "/etc/azure-mail/brand.env"))
API_EMAIL = "2023-03-31"
API_ACS = "2025-09-01"
MGMT = "https://management.azure.com"


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        sys.exit(f"Missing {path}. Copy azure-mail/vm/brand.env.example there.")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def http_json(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    body: dict | bytes | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 60,
) -> tuple[int, object]:
    data = None
    hdrs = dict(headers or {})
    if isinstance(body, dict):
        data = json.dumps(body).encode()
        hdrs.setdefault("Content-Type", "application/json")
    elif isinstance(body, bytes):
        data = body
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    if auth:
        import base64

        tok = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        req.add_header("Authorization", f"Basic {tok}")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        code = e.code
        if code >= 400:
            raise RuntimeError(f"{method} {url} -> {code} {raw[:800]!r}") from e
    if not raw:
        return code, {}
    try:
        return code, json.loads(raw.decode())
    except json.JSONDecodeError:
        return code, raw.decode(errors="replace")


def azure_token(env: dict[str, str]) -> str:
    tenant = env["AZURE_TENANT_ID"]
    data = urllib.parse.urlencode(
        {
            "client_id": env["AZURE_CLIENT_ID"],
            "client_secret": env["AZURE_CLIENT_SECRET"],
            "grant_type": "client_credentials",
            "scope": "https://management.azure.com/.default",
        }
    ).encode()
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        tok = json.load(resp)
    return tok["access_token"]


def az(env: dict[str, str], method: str, path: str, api: str, body: dict | None = None):
    url = f"{MGMT}{path}?api-version={api}"
    token = azure_token(env)
    return http_json(
        method,
        url,
        headers={"Authorization": f"Bearer {token}"},
        body=body,
    )[1]


def mailcow(env: dict[str, str], method: str, route: str, body: dict | None = None):
    base = env["MAILCOW_API_URL"].rstrip("/")
    key = env.get("MAILCOW_API_KEY") or ""
    if not key:
        sys.exit("Set MAILCOW_API_KEY in /etc/azure-mail/brand.env (Mailcow admin → Access → API).")
    return http_json(
        method,
        f"{base}{route}",
        headers={"X-API-Key": key, "Accept": "application/json"},
        body=body,
    )[1]


def namecom_add(env: dict[str, str], domain: str, rec: dict) -> None:
    user, token = env.get("NAMECOM_USER") or "", env.get("NAMECOM_TOKEN") or ""
    if not user or not token:
        return
    _, existing = http_json(
        "GET",
        f"https://api.name.com/v4/domains/{domain}/records",
        auth=(user, token),
    )
    recs = existing.get("records") or [] if isinstance(existing, dict) else []
    host = rec.get("host") or ""
    typ = rec["type"]
    answer = rec["answer"]
    for r in recs:
        if (r.get("host") or "") == host and r.get("type") == typ and str(r.get("answer") or "") == answer:
            print(f"  Name.com already has {typ} {host or '@'} -> {answer[:60]}")
            return
    http_json(
        "POST",
        f"https://api.name.com/v4/domains/{domain}/records",
        auth=(user, token),
        body=rec,
    )
    print(f"  Name.com added {typ} {host or '@'} -> {answer[:60]}")


def dns_rows(domain_obj: dict, domain: str) -> list[tuple[str, str, str, str]]:
    vr = (domain_obj.get("properties") or {}).get("verificationRecords") or {}
    rows = []
    for kind in ("Domain", "SPF", "DKIM", "DKIM2"):
        x = vr.get(kind) or {}
        typ = x.get("type") or ("CNAME" if kind.startswith("DKIM") else "TXT")
        name = x.get("name") or "@"
        val = x.get("value") or ""
        suffix = "." + domain
        if name.endswith(suffix):
            name = name[: -len(suffix)]
        if name in ("", "@", domain):
            name = ""
        rows.append((kind, typ, name, val))
    return rows


def add_mailcow(env: dict[str, str], domain: str, local: str, password: str) -> None:
    print("Mailcow domain...")
    mailcow(
        env,
        "POST",
        "/api/v1/add/domain",
        {
            "domain": domain,
            "description": "add-brand",
            "aliases": 400,
            "mailboxes": 50,
            "defquota": 3072,
            "maxquota": 10240,
            "quota": 10240,
            "active": "1",
            "restart_sogo": "1",
        },
    )
    print("Mailcow mailbox...")
    mailcow(
        env,
        "POST",
        "/api/v1/add/mailbox",
        {
            "local_part": local,
            "domain": domain,
            "name": local,
            "quota": "0",
            "password": password,
            "password2": password,
            "active": "1",
            "force_pw_update": "0",
            "tls_enforce_in": "1",
            "tls_enforce_out": "1",
        },
    )


def add_acs(env: dict[str, str], domain: str, locals_: list[str], mail_host: str) -> None:
    sub = env["AZURE_SUBSCRIPTION_ID"]
    rg = env["RESOURCE_GROUP"]
    email = env["EMAIL_NAME"]
    acs = env["ACS_NAME"]
    email_id = (
        f"/subscriptions/{sub}/resourceGroups/{rg}/providers/"
        f"Microsoft.Communication/emailServices/{email}"
    )
    acs_id = (
        f"/subscriptions/{sub}/resourceGroups/{rg}/providers/"
        f"Microsoft.Communication/CommunicationServices/{acs}"
    )
    dom_id = f"{email_id}/domains/{domain}"
    managed = f"{email_id}/domains/AzureManagedDomain"

    print("ACS custom domain...")
    obj = az(
        env,
        "PUT",
        dom_id,
        API_EMAIL,
        {"location": "global", "properties": {"domainManagement": "CustomerManaged"}},
    )
    rows = dns_rows(obj if isinstance(obj, dict) else {}, domain)
    print()
    print(f"DNS for {domain}:")
    print(f"  MX     @ (or blank)    {mail_host}.   priority 10")
    for kind, typ, host, val in rows:
        print(f"  {typ:6} {host or '@':40} {val}")
    print()

    mx = {
        "host": "",
        "type": "MX",
        "answer": mail_host + ".",
        "ttl": 300,
        "priority": 10,
    }
    namecom_add(env, domain, mx)
    for kind, typ, host, val in rows:
        rec = {"host": host, "type": typ, "answer": val, "ttl": 300}
        namecom_add(env, domain, rec)

    if not (env.get("NAMECOM_USER") and env.get("NAMECOM_TOKEN")):
        print("No NAMECOM_* in env — paste the DNS rows at the registrar, then re-run if verify is still pending.")

    def status(kind: str) -> str:
        d = az(env, "GET", dom_id, API_EMAIL)
        vs = (d.get("properties") or {}).get("verificationStates") or {}
        return (vs.get(kind) or {}).get("status") or "Unknown"

    for kind in ("Domain", "SPF", "DKIM", "DKIM2"):
        try:
            az(env, "POST", f"{dom_id}/initiateVerification", API_EMAIL, {"verificationType": kind})
        except RuntimeError as e:
            print(f"  initiate {kind}: {e}")

    print("Waiting for ACS Verified (up to 10 min)...")
    ok = False
    for i in range(1, 21):
        st = {k: status(k) for k in ("Domain", "SPF", "DKIM", "DKIM2")}
        print(f"  [{i}] {st}")
        if all(v == "Verified" for v in st.values()):
            ok = True
            break
        time.sleep(30)
    if not ok:
        sys.exit("DNS not verified yet. Fix records (apex SPF on @, not domain.domain) and re-run.")

    print("Linking to ACS (keep existing linked domains)...")
    cur = az(env, "GET", acs_id, API_ACS)
    linked = list((cur.get("properties") or {}).get("linkedDomains") or [])
    for extra in (managed, dom_id):
        if extra not in linked:
            linked.append(extra)
    az(env, "PATCH", acs_id, API_ACS, {"properties": {"linkedDomains": linked}})

    print("MailFrom...")
    for user in locals_:
        try:
            az(
                env,
                "PUT",
                f"{dom_id}/senderUsernames/{user}",
                API_EMAIL,
                {"properties": {"username": user, "displayName": user}},
            )
            print(f"  {user}@{domain}")
        except RuntimeError as e:
            print(f"  {user}@{domain} failed (often quota=1 DoNotReply). Rename DoNotReply -> {user} once, or: {e}")


def main() -> None:
    p = argparse.ArgumentParser(description="Create mailbox + ACS send domain from the mail VM.")
    p.add_argument("domain", help="example.com")
    p.add_argument("local_part", nargs="?", default="hi", help="mailbox local part (default hi)")
    p.add_argument("--password", default="", help="mailbox password (random if omitted)")
    p.add_argument("--skip-mailcow", action="store_true")
    p.add_argument("--skip-acs", action="store_true")
    args = p.parse_args()
    env = load_env(ENV_PATH)
    domain = args.domain.lower().strip().rstrip(".")
    local = args.local_part.strip()
    password = args.password or (os.urandom(9).hex() + "Aa1")
    mail_host = env.get("MAIL_HOSTNAME") or "mail.seethinajayadileep.dev"

    if not args.skip_mailcow:
        add_mailcow(env, domain, local, password)
    if not args.skip_acs:
        add_acs(env, domain, [local], mail_host)

    print()
    print("OK")
    print(f"  Webmail  https://{mail_host}/")
    print(f"  Login    {local}@{domain}")
    print(f"  Password {password}")
    print("  IMAP 993 / SMTP submission 587  host", mail_host)


if __name__ == "__main__":
    main()
