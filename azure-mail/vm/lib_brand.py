"""Shared Azure + Mailcow + multi-registrar DNS helpers."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ENV_PATH = Path(os.environ.get("AZURE_MAIL_ENV", "/etc/azure-mail/brand.env"))
PROVIDERS_PATH = Path(os.environ.get("AZURE_MAIL_PROVIDERS", "/etc/azure-mail/providers.json"))
DOMAINS_PATH = Path(os.environ.get("AZURE_MAIL_DOMAINS", "/etc/azure-mail/domains.json"))
SSO_KEY_PATH = Path(os.environ.get("MAILCOW_SSO_KEY", "/opt/mailcow-dockerized/data/web/inc/.mailbox-sso.key"))
SSO_TTL = 90
API_EMAIL = "2023-03-31"
API_ACS = "2025-09-01"
MGMT = "https://management.azure.com"

LogFn = Callable[[str], None]


@dataclass
class DnsRecord:
    type: str
    host: str
    value: str
    priority: int | None = None
    kind: str = ""


@dataclass
class ProviderSpec:
    id: str
    name: str
    fields: list[tuple[str, str, str]]  # key, label, input type
    help: str


PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        "hostinger",
        "Hostinger",
        [("token", "API token", "password")],
        "hPanel → Account → API. Token needs DNS permission.",
    ),
    ProviderSpec(
        "godaddy",
        "GoDaddy",
        [("key", "API key", "text"), ("secret", "API secret", "password")],
        "developer.godaddy.com production key. DNS API often needs 10+ domains or Discount Domain Club.",
    ),
    ProviderSpec(
        "cloudflare",
        "Cloudflare",
        [("token", "API token", "password")],
        "My Profile → API Tokens → Edit zone DNS. Keep mail records DNS-only (grey cloud).",
    ),
    ProviderSpec(
        "namecom",
        "Name.com",
        [("user", "Username", "text"), ("token", "API token", "password")],
        "name.com → API. Used for seethinajayadileep.dev today.",
    ),
    ProviderSpec(
        "namecheap",
        "Namecheap",
        [
            ("user", "API user", "text"),
            ("key", "API key", "password"),
            ("username", "Username", "text"),
            ("client_ip", "Whitelisted IP", "text"),
        ],
        "Profile → Tools → API Access. Whitelist the mail VM IP (4.224.47.183).",
    ),
    ProviderSpec(
        "porkbun",
        "Porkbun",
        [("key", "API key", "text"), ("secret", "Secret key", "password")],
        "porkbun.com → Account → API. Enable API access per domain if asked.",
    ),
]


def load_env(path: Path | None = None) -> dict[str, str]:
    path = path or ENV_PATH
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def write_env(values: dict[str, str], path: Path | None = None) -> None:
    path = path or ENV_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_SUBSCRIPTION_ID",
        "RESOURCE_GROUP",
        "ACS_NAME",
        "EMAIL_NAME",
        "MAILCOW_API_URL",
        "MAILCOW_API_KEY",
        "MAIL_HOSTNAME",
        "WEB_ADMIN_PASSWORD",
        "WEB_SECRET",
        "WEB_SSO_SECRET",
        "NAMECOM_USER",
        "NAMECOM_TOKEN",
    ]
    current = load_env(path)
    current.update({k: v for k, v in values.items() if v is not None})
    lines = ["# azure-mail — chmod 600, do not commit"]
    for k in keys:
        lines.append(f"{k}={current.get(k, '')}")
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def load_providers(path: Path | None = None) -> dict:
    path = path or PROVIDERS_PATH
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def load_domains(path: Path | None = None) -> dict:
    path = path or DOMAINS_PATH
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_domain(info: dict, path: Path | None = None) -> None:
    path = path or DOMAINS_PATH
    store = load_domains(path)
    domain = (info.get("domain") or "").lower()
    if domain:
        prev = store.get(domain) or {}
        merged = {**prev, **info, "domain": domain}
        store[domain] = merged
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(store, indent=2) + "\n")
        os.chmod(path, 0o600)


def acs_paths(env: dict[str, str], domain: str) -> tuple[str, str, str, str]:
    sub = env.get("AZURE_SUBSCRIPTION_ID") or ""
    rg = env.get("RESOURCE_GROUP") or "mailboxRg"
    email = env.get("EMAIL_NAME") or "mail-box"
    acs = env.get("ACS_NAME") or "mailboxCs"
    email_id = (
        f"/subscriptions/{sub}/resourceGroups/{rg}/providers/"
        f"Microsoft.Communication/emailServices/{email}"
    )
    acs_id = (
        f"/subscriptions/{sub}/resourceGroups/{rg}/providers/"
        f"Microsoft.Communication/CommunicationServices/{acs}"
    )
    return email_id, acs_id, f"{email_id}/domains/{domain}", f"{email_id}/domains/AzureManagedDomain"


def verification_status(env: dict[str, str], domain: str) -> dict[str, str]:
    _email_id, _acs_id, dom_id, _managed = acs_paths(env, domain)
    d = az(env, "GET", dom_id, API_EMAIL)
    vs = (d.get("properties") or {}).get("verificationStates") or {}
    return {k: (vs.get(k) or {}).get("status") or "Unknown" for k in ("Domain", "SPF", "DKIM", "DKIM2")}


FAILED_STATES = ("VerificationFailed", "Failed", "Canceled", "Cancelled")
LINK_KEYS = ("Domain", "SPF", "DKIM", "DKIM2")


def can_link_sender(st: dict[str, str]) -> bool:
    """Domain TXT proved ownership. Azure still will not attach the domain until SPF/DKIM pass."""
    return (st.get("Domain") or "") == "Verified"


def can_link_domain(st: dict[str, str]) -> bool:
    """ACS PATCH linkedDomains only accepts a fully verified custom domain."""
    return all((st.get(k) or "") == "Verified" for k in LINK_KEYS)


def link_refused(exc: BaseException) -> bool:
    text = str(exc)
    return "PatchDomainLinkingError" in text or "could not be linked" in text.lower()


def check_failed(status: str) -> bool:
    return (status or "") in FAILED_STATES


def linked_domain_name(item: object) -> str:
    """Parse a custom domain from an ACS linkedDomains resource id or hostname."""
    text = str(item or "").strip().rstrip("/")
    if not text:
        return ""
    name = text.split("/")[-1] if "/domains/" in text.lower() else text
    name = name.lower().rstrip(".")
    if not name or name == "azuremanageddomain" or "." not in name:
        return ""
    return name


def linked_domain_names(env: dict[str, str]) -> set[str] | None:
    """One ACS GET of linkedDomains. None if Azure is not configured or the call fails."""
    if not azure_ready(env):
        return None
    try:
        _email_id, acs_id, _dom_id, _managed = acs_paths(env, "x")
        cur = az(env, "GET", acs_id, API_ACS)
    except Exception:  # noqa: BLE001 — Central mail still uses saved flags
        return None
    names: set[str] = set()
    for item in (cur.get("properties") or {}).get("linkedDomains") or []:
        name = linked_domain_name(item)
        if name:
            names.add(name)
    return names


def domain_linked(env: dict[str, str], domain: str) -> bool:
    names = linked_domain_names(env)
    if names is None:
        return False
    return domain.lower().strip().rstrip(".") in names


def _initiate(env: dict[str, str], dom_id: str, kind: str, log: LogFn) -> None:
    try:
        az(env, "POST", f"{dom_id}/initiateVerification", API_EMAIL, {"verificationType": kind})
        log(f"Asked Azure to check {kind}")
    except RuntimeError as e:
        log(f"  {kind}: {e}")


def link_and_mailfrom(env: dict[str, str], domain: str, locals_: list[str], log: LogFn) -> None:
    """GET current linkedDomains, then append. Never replace the list."""
    _email_id, acs_id, dom_id, managed = acs_paths(env, domain)
    cur = az(env, "GET", acs_id, API_ACS)
    linked = list((cur.get("properties") or {}).get("linkedDomains") or [])
    changed = False
    for extra in (managed, dom_id):
        if extra not in linked:
            linked.append(extra)
            changed = True
    if changed:
        try:
            az(env, "PATCH", acs_id, API_ACS, {"properties": {"linkedDomains": linked}})
            log("Linked domain for Azure send (stops 501 5.1.7).")
        except RuntimeError as exc:
            if link_refused(exc):
                log(
                    "Azure refused to link yet (PatchDomainLinkingError). "
                    "mailboxCs only accepts a domain after Domain, SPF, DKIM, and DKIM2 are all Verified. "
                    "Finish those DNS checks, then click Verify again."
                )
                return
            raise
    else:
        log("Domain already linked for Azure send.")
    for user in locals_:
        if not user:
            continue
        try:
            az(
                env,
                "PUT",
                f"{dom_id}/senderUsernames/{user}",
                API_EMAIL,
                {"properties": {"username": user, "displayName": user}},
            )
            log(f"  MailFrom {user}@{domain}")
        except RuntimeError as e:
            log(f"  MailFrom {user}@{domain}: {e}")


def verify_acs(env: dict[str, str], domain: str, locals_: list[str], log: LogFn) -> dict[str, str]:
    """Retry Failed checks (TXT added late). Link only after Azure will accept the domain."""
    _email_id, _acs_id, dom_id, _managed = acs_paths(env, domain)
    st = verification_status(env, domain)
    for kind, status in st.items():
        if status == "Verified":
            continue
        _initiate(env, dom_id, kind, log)
    linked_ok = False
    for i in range(1, 7):
        st = verification_status(env, domain)
        pending = [k for k, v in st.items() if v != "Verified"]
        log(f"  Check {i}/6  pending: {', '.join(pending) or 'none'}  {st}")
        if can_link_domain(st) and not linked_ok:
            link_and_mailfrom(env, domain, locals_, log)
            linked_ok = True
        elif can_link_sender(st) and pending and not linked_ok:
            log(
                "Domain TXT is Verified. Azure will not link mailboxCs until "
                f"{', '.join(pending)} are Verified too."
            )
        if all(v == "Verified" for v in st.values()):
            if not linked_ok:
                link_and_mailfrom(env, domain, locals_, log)
            return st
        for kind, status in st.items():
            if check_failed(status):
                log(f"{kind} failed ({status}) — DNS may have been added late. Retrying.")
                _initiate(env, dom_id, kind, log)
        time.sleep(10)
    if can_link_domain(st) and not linked_ok:
        link_and_mailfrom(env, domain, locals_, log)
    return st


def save_providers(data: dict, path: Path | None = None) -> None:
    path = path or PROVIDERS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(path, 0o600)


def provider_connected(creds: dict | None) -> bool:
    return bool(creds) and all(str(v).strip() for v in creds.values())


def connected_ids(store: dict | None = None) -> list[str]:
    store = store if store is not None else load_providers()
    return [p.id for p in PROVIDERS if provider_connected(store.get(p.id))]


def http_json(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    body: dict | list | bytes | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 60,
    accept_empty: bool = True,
) -> tuple[int, object]:
    data = None
    hdrs = dict(headers or {})
    if isinstance(body, (dict, list)):
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
        if accept_empty:
            return code, {}
        return code, {}
    try:
        return code, json.loads(raw.decode())
    except json.JSONDecodeError:
        return code, raw.decode(errors="replace")


def azure_token(env: dict[str, str]) -> str:
    tenant = env.get("AZURE_TENANT_ID") or ""
    if not tenant:
        raise RuntimeError("Azure is not configured. Add the Entra app on Setup.")
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
    if "access_token" not in tok:
        raise RuntimeError(f"Azure login failed: {tok}")
    return tok["access_token"]


def az(env: dict[str, str], method: str, path: str, api: str, body: dict | None = None):
    url = f"{MGMT}{path}?api-version={api}"
    token = azure_token(env)
    return http_json(method, url, headers={"Authorization": f"Bearer {token}"}, body=body)[1]


def mailcow(env: dict[str, str], method: str, route: str, body: dict | None = None):
    base = (env.get("MAILCOW_API_URL") or "").rstrip("/")
    key = env.get("MAILCOW_API_KEY") or ""
    if not base or not key:
        raise RuntimeError("Mailcow API URL and key are required (Setup page).")
    return http_json(
        method,
        f"{base}{route}",
        headers={"X-API-Key": key, "Accept": "application/json"},
        body=body,
    )[1]


def _as_rows(result: object) -> list:
    if isinstance(result, list):
        return [x for x in result if isinstance(x, dict)]
    if isinstance(result, dict):
        for key in ("items", "data"):
            if isinstance(result.get(key), list):
                return [x for x in result[key] if isinstance(x, dict)]
    return []


def _is_on(value: object) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "active")


def list_mailcow_domains(env: dict[str, str]) -> list[dict]:
    rows = []
    for item in _as_rows(mailcow(env, "GET", "/api/v1/get/domain/all")):
        name = (item.get("domain_name") or item.get("domain") or "").strip().lower().rstrip(".")
        if "." not in name:
            continue
        rows.append({"domain": name, "active": _is_on(item.get("active", "1"))})
    return rows


def list_mailcow_mailboxes(env: dict[str, str]) -> list[dict]:
    rows = []
    for item in _as_rows(mailcow(env, "GET", "/api/v1/get/mailbox/all")):
        user = str(item.get("username") or "").strip()
        local = str(item.get("local_part") or "").strip()
        domain = str(item.get("domain") or "").strip().lower().rstrip(".")
        if "@" in user:
            local = local or user.split("@", 1)[0]
            domain = domain or user.split("@", 1)[1].lower()
        if not domain or "." not in domain:
            continue
        if not user:
            user = f"{local}@{domain}" if local else ""
        if not user:
            continue
        rows.append(
            {
                "email": user,
                "local_part": local or user.split("@", 1)[0],
                "domain": domain,
                "name": str(item.get("name") or local or user.split("@", 1)[0]),
                "active": _is_on(item.get("active", "1")),
            }
        )
    return rows


def mail_directory(env: dict[str, str]) -> dict:
    """Central view: Mailcow domains + mailboxes, plus live Azure send state."""
    saved = load_domains()
    mail_host = env.get("MAIL_HOSTNAME") or "mail.seethinajayadileep.dev"
    error = None
    cow_domains: list[dict] = []
    cow_boxes: list[dict] = []
    try:
        cow_domains = list_mailcow_domains(env)
        cow_boxes = list_mailcow_mailboxes(env)
    except Exception as exc:  # noqa: BLE001 — still show saved domains if Mailcow is down
        error = str(exc)

    live_linked = linked_domain_names(env)

    def send_ready_of(name: str, info: dict) -> bool:
        if live_linked is not None:
            return name in live_linked
        return bool(info.get("send_ready") or info.get("verified"))

    by_domain: dict[str, dict] = {}

    def ensure(name: str, source: str) -> dict:
        name = name.lower().strip().rstrip(".")
        row = by_domain.get(name)
        if not row:
            info = saved.get(name) or {}
            row = {
                "domain": name,
                "active": True,
                "mailboxes": [],
                "source": source,
                "send_ready": send_ready_of(name, info),
                "saved": info,
            }
            by_domain[name] = row
        return row

    for item in cow_domains:
        row = ensure(item["domain"], "mailcow")
        row["active"] = item["active"]
        row["source"] = "mailcow"
    for box in cow_boxes:
        row = ensure(box["domain"], "mailcow")
        row["mailboxes"].append(box)
    # Leftover saved-only rows (test.example after a Mailcow delete) stay hidden
    # while Mailcow answers. If Mailcow is down, fall back to the saved list.
    if error is not None:
        for name, info in saved.items():
            if "." not in name:
                continue
            row = ensure(name, "saved")
            if not row["mailboxes"] and info.get("email"):
                row["mailboxes"].append(
                    {
                        "email": info["email"],
                        "local_part": info.get("local_part") or str(info["email"]).split("@")[0],
                        "domain": name,
                        "name": info.get("local_part") or "",
                        "active": True,
                        "from_saved": True,
                    }
                )
    if live_linked is not None:
        for name, info in saved.items():
            ready = name in live_linked
            if bool(info.get("send_ready")) != ready or bool(info.get("verified")) != ready:
                updated = dict(info)
                updated["send_ready"] = ready
                updated["verified"] = ready
                updated["linked"] = ready
                save_domain(updated)
    for row in by_domain.values():
        seen: set[str] = set()
        unique = []
        for box in sorted(row["mailboxes"], key=lambda x: x.get("email") or ""):
            email = (box.get("email") or "").lower()
            if not email or email in seen:
                continue
            seen.add(email)
            unique.append(box)
        row["mailboxes"] = unique
    rows = sorted(by_domain.values(), key=lambda x: x["domain"])
    return {
        "domains": rows,
        "domain_count": len(rows),
        "mailbox_count": sum(len(r["mailboxes"]) for r in rows),
        "error": error,
        "webmail": f"https://{mail_host}/",
    }


def persist_sso_secret(env: dict[str, str] | None = None) -> str:
    """Keep a HMAC key in brand.env and in Mailcow's web tree for mailbox-sso.php."""
    env = dict(env or load_env())
    secret = (env.get("WEB_SSO_SECRET") or "").strip()
    if not secret:
        secret = secrets.token_hex(32)
        write_env({"WEB_SSO_SECRET": secret})
    try:
        if SSO_KEY_PATH.parent.is_dir():
            current = SSO_KEY_PATH.read_text().strip() if SSO_KEY_PATH.is_file() else ""
            if current != secret:
                SSO_KEY_PATH.write_text(secret + "\n")
                os.chmod(SSO_KEY_PATH, 0o644)
    except OSError:
        pass
    return secret


def webmail_ticket(email: str, secret: str, now: int | None = None, ttl: int = SSO_TTL) -> str:
    email = (email or "").strip().lower()
    exp = str((now if now is not None else int(time.time())) + int(ttl))
    sig = hmac.new(secret.encode(), f"{email}.{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def webmail_sso_url(env: dict[str, str], email: str, now: int | None = None) -> str:
    email = (email or "").strip().lower()
    host = env.get("MAIL_HOSTNAME") or "mail.seethinajayadileep.dev"
    secret = persist_sso_secret(env)
    ticket = webmail_ticket(email, secret, now=now)
    return f"https://{host}/mailbox-sso.php?{urllib.parse.urlencode({'u': email, 't': ticket})}"


def mailbox_known(env: dict[str, str], email: str) -> bool:
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.split("@", 1)[1]:
        return False
    try:
        for box in list_mailcow_mailboxes(env):
            if (box.get("email") or "").lower() == email:
                return True
    except Exception:
        pass
    for info in load_domains().values():
        if (info.get("email") or "").lower() == email:
            return True
    return False


def apex_host(host: str, domain: str) -> str:
    host = (host or "").strip()
    suffix = "." + domain
    if host.endswith(suffix):
        host = host[: -len(suffix)]
    if host in ("", "@", domain):
        return ""
    return host


def display_host(host: str) -> str:
    return host or "@"


def provisioning_state(obj: dict) -> str:
    props = obj.get("properties") or {}
    return str(props.get("provisioningState") or obj.get("provisioningState") or "")


def records_ready(obj: dict) -> bool:
    vr = (obj.get("properties") or {}).get("verificationRecords") or {}
    for kind in ("Domain", "SPF", "DKIM", "DKIM2"):
        val = ((vr.get(kind) or {}).get("value") or "").strip()
        if not val:
            return False
    return True


def dns_rows(domain_obj: dict, domain: str) -> list[DnsRecord]:
    vr = (domain_obj.get("properties") or {}).get("verificationRecords") or {}
    rows: list[DnsRecord] = []
    for kind in ("Domain", "SPF", "DKIM", "DKIM2"):
        x = vr.get(kind) or {}
        val = (x.get("value") or "").strip()
        if not val:
            continue
        typ = x.get("type") or ("CNAME" if kind.startswith("DKIM") else "TXT")
        name = apex_host(x.get("name") or "", domain)
        rows.append(DnsRecord(type=typ, host=name, value=val, kind=kind))
    return rows


def wait_acs_domain(env: dict[str, str], dom_id: str, log: LogFn) -> dict:
    """PUT is async — records are empty while provisioningState is Accepted."""
    obj: dict = {}
    for i in range(1, 9):
        got = az(env, "GET", dom_id, API_EMAIL)
        obj = got if isinstance(got, dict) else {}
        state = provisioning_state(obj)
        ready = records_ready(obj)
        log(f"  Azure domain state {i}/8: {state or 'unknown'} records={'ready' if ready else 'pending'}")
        if ready and state.lower() in ("", "succeeded", "updating"):
            return obj
        time.sleep(5)
    return obj


def mail_records(domain: str, mail_host: str, acs_rows: list[DnsRecord]) -> list[DnsRecord]:
    mx = DnsRecord(type="MX", host="", value=mail_host.rstrip(".") + ".", priority=10, kind="MX")
    dmarc = DnsRecord(type="TXT", host="_dmarc", value="v=DMARC1; p=none;", kind="DMARC")
    return [mx, *acs_rows, dmarc]


def paste_block(recs: list[dict]) -> str:
    lines = ["Type\tHost\tPriority\tValue"]
    for r in recs:
        lines.append(f"{r.get('type','')}\t{r.get('host','@')}\t{r.get('priority') or ''}\t{r.get('value','')}")
    return "\n".join(lines)


def log_dns(recs: list[DnsRecord], log: LogFn) -> None:
    log("Add these DNS records at Hostinger / GoDaddy / Name.com (or any DNS panel):")
    log("  Type    Host   Priority  Value")
    for r in format_records(recs):
        pri = str(r.get("priority") or "")
        log(f"  {r['type']:6}  {r['host']:8}  {pri:8}  {r['value']}")
    log("Apex SPF and MX go on @ (blank host), not domain.domain.")


def azure_ready(env: dict[str, str]) -> bool:
    return bool(
        env.get("AZURE_TENANT_ID")
        and env.get("AZURE_CLIENT_ID")
        and env.get("AZURE_CLIENT_SECRET")
        and env.get("AZURE_SUBSCRIPTION_ID")
    )


def lookup_dns(env: dict[str, str], domain: str) -> list[dict]:
    domain = domain.lower().strip().rstrip(".")
    mail_host = env.get("MAIL_HOSTNAME") or "mail.seethinajayadileep.dev"
    recs = mail_records(domain, mail_host, [])
    if not azure_ready(env):
        return format_records(recs)
    try:
        sub = env["AZURE_SUBSCRIPTION_ID"]
        rg = env.get("RESOURCE_GROUP") or "mailboxRg"
        email = env.get("EMAIL_NAME") or "mail-box"
        path = (
            f"/subscriptions/{sub}/resourceGroups/{rg}/providers/"
            f"Microsoft.Communication/emailServices/{email}/domains/{domain}"
        )
        obj = az(env, "GET", path, API_EMAIL)
        if isinstance(obj, dict):
            recs = mail_records(domain, mail_host, dns_rows(obj, domain))
    except Exception:  # noqa: BLE001 — still show MX/DMARC if Azure is unreachable
        pass
    return format_records(recs)


def format_records(recs: list[DnsRecord]) -> list[dict]:
    out = []
    for r in recs:
        row = {"kind": r.kind or r.type, "type": r.type, "host": display_host(r.host), "value": r.value}
        if r.priority is not None:
            row["priority"] = r.priority
        out.append(row)
    return out


def apply_dns(provider: str, creds: dict, domain: str, recs: list[DnsRecord], log: LogFn) -> None:
    fn = {
        "hostinger": _dns_hostinger,
        "godaddy": _dns_godaddy,
        "cloudflare": _dns_cloudflare,
        "namecom": _dns_namecom,
        "namecheap": _dns_namecheap,
        "porkbun": _dns_porkbun,
        "manual": None,
    }.get(provider)
    if provider == "manual" or fn is None:
        log("Manual DNS — copy the records at your registrar.")
        return
    if not provider_connected(creds):
        raise RuntimeError(f"{provider} is not connected.")
    fn(creds, domain, recs, log)


def _dns_hostinger(creds: dict, domain: str, recs: list[DnsRecord], log: LogFn) -> None:
    zone = []
    for r in recs:
        content = r.value
        if r.type == "MX" and r.priority is not None:
            content = f"{r.priority} {r.value}"
        zone.append(
            {
                "name": display_host(r.host),
                "type": r.type,
                "ttl": 300,
                "records": [{"content": content}],
            }
        )
    http_json(
        "PUT",
        f"https://developers.hostinger.com/api/dns/v1/zones/{domain}",
        headers={"Authorization": f"Bearer {creds['token']}"},
        body={"overwrite": True, "zone": zone},
    )
    log(f"Hostinger updated {len(recs)} records for {domain}")


def _dns_godaddy(creds: dict, domain: str, recs: list[DnsRecord], log: LogFn) -> None:
    payload = []
    for r in recs:
        item = {
            "type": r.type,
            "name": display_host(r.host),
            "data": r.value,
            "ttl": 600,
        }
        if r.priority is not None:
            item["priority"] = r.priority
        payload.append(item)
    http_json(
        "PATCH",
        f"https://api.godaddy.com/v1/domains/{domain}/records",
        headers={"Authorization": f"sso-key {creds['key']}:{creds['secret']}"},
        body=payload,
    )
    log(f"GoDaddy appended {len(recs)} records for {domain}")


def _cf_zone(token: str, domain: str) -> str:
    _, data = http_json(
        "GET",
        "https://api.cloudflare.com/client/v4/zones?" + urllib.parse.urlencode({"name": domain}),
        headers={"Authorization": f"Bearer {token}"},
    )
    results = (data or {}).get("result") if isinstance(data, dict) else None
    if not results:
        raise RuntimeError(f"Cloudflare has no zone named {domain}")
    return results[0]["id"]


def _dns_cloudflare(creds: dict, domain: str, recs: list[DnsRecord], log: LogFn) -> None:
    token = creds["token"]
    zone = _cf_zone(token, domain)
    _, existing = http_json(
        "GET",
        f"https://api.cloudflare.com/client/v4/zones/{zone}/dns_records?per_page=200",
        headers={"Authorization": f"Bearer {token}"},
    )
    have = existing.get("result") or [] if isinstance(existing, dict) else []
    for r in recs:
        name = r.host + "." + domain if r.host else domain
        body = {
            "type": r.type,
            "name": name,
            "content": r.value.rstrip(".") if r.type != "TXT" else r.value,
            "ttl": 300,
            "proxied": False,
        }
        if r.priority is not None:
            body["priority"] = r.priority
        match = next(
            (
                h
                for h in have
                if h.get("type") == r.type
                and h.get("name") in (name, name.rstrip("."))
                and str(h.get("content") or "") in (r.value, r.value.rstrip("."))
            ),
            None,
        )
        if match:
            log(f"  Cloudflare already has {r.type} {display_host(r.host)}")
            continue
        http_json(
            "POST",
            f"https://api.cloudflare.com/client/v4/zones/{zone}/dns_records",
            headers={"Authorization": f"Bearer {token}"},
            body=body,
        )
        log(f"  Cloudflare added {r.type} {display_host(r.host)}")


def _dns_namecom(creds: dict, domain: str, recs: list[DnsRecord], log: LogFn) -> None:
    auth = (creds["user"], creds["token"])
    _, existing = http_json("GET", f"https://api.name.com/v4/domains/{domain}/records", auth=auth)
    have = existing.get("records") or [] if isinstance(existing, dict) else []
    for r in recs:
        rec = {"host": r.host, "type": r.type, "answer": r.value, "ttl": 300}
        if r.priority is not None:
            rec["priority"] = r.priority
        if any(
            (x.get("host") or "") == r.host
            and x.get("type") == r.type
            and str(x.get("answer") or "") == r.value
            for x in have
        ):
            log(f"  Name.com already has {r.type} {display_host(r.host)}")
            continue
        http_json("POST", f"https://api.name.com/v4/domains/{domain}/records", auth=auth, body=rec)
        log(f"  Name.com added {r.type} {display_host(r.host)}")


def _namecheap_split(domain: str) -> tuple[str, str]:
    parts = domain.split(".")
    if len(parts) < 2:
        raise RuntimeError(f"Bad domain {domain}")
    return ".".join(parts[:-1]), parts[-1]


def _namecheap_call(creds: dict, command: str, extra: dict[str, str]) -> ET.Element:
    q = {
        "ApiUser": creds["user"],
        "ApiKey": creds["key"],
        "UserName": creds.get("username") or creds["user"],
        "ClientIp": creds.get("client_ip") or "4.224.47.183",
        "Command": command,
    }
    q.update(extra)
    url = "https://api.namecheap.com/xml.response?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        xml = resp.read()
    root = ET.fromstring(xml)
    status = root.attrib.get("Status")
    if status != "OK":
        err = "".join(root.itertext())
        raise RuntimeError(f"Namecheap {command} failed: {err[:400]}")
    return root


def _dns_namecheap(creds: dict, domain: str, recs: list[DnsRecord], log: LogFn) -> None:
    sld, tld = _namecheap_split(domain)
    root = _namecheap_call(creds, "namecheap.domains.dns.getHosts", {"SLD": sld, "TLD": tld})
    ns = {"n": "http://api.namecheap.com/xml.response"}
    hosts = list(root.findall(".//n:host", ns)) or list(root.findall(".//host"))
    keep: list[dict[str, str]] = []
    skip_types = {(r.type, display_host(r.host)) for r in recs}
    for h in hosts:
        typ = h.attrib.get("Type") or h.attrib.get("type") or ""
        name = h.attrib.get("Name") or h.attrib.get("name") or "@"
        if (typ, name) in skip_types:
            continue
        keep.append(
            {
                "type": typ,
                "host": name,
                "value": h.attrib.get("Address") or h.attrib.get("address") or "",
                "ttl": h.attrib.get("TTL") or "300",
                "mxpref": h.attrib.get("MXPref") or "",
            }
        )
    extra = {"SLD": sld, "TLD": tld}
    i = 1
    for h in keep:
        extra[f"HostName{i}"] = h["host"]
        extra[f"RecordType{i}"] = h["type"]
        extra[f"Address{i}"] = h["value"]
        extra[f"TTL{i}"] = h["ttl"]
        if h["type"] == "MX" and h["mxpref"]:
            extra[f"MXPref{i}"] = h["mxpref"]
        i += 1
    for r in recs:
        extra[f"HostName{i}"] = display_host(r.host)
        extra[f"RecordType{i}"] = r.type
        extra[f"Address{i}"] = r.value
        extra[f"TTL{i}"] = "300"
        if r.priority is not None:
            extra[f"MXPref{i}"] = str(r.priority)
        i += 1
    _namecheap_call(creds, "namecheap.domains.dns.setHosts", extra)
    log(f"Namecheap replaced hosts for {domain} (kept non-mail records)")


def _dns_porkbun(creds: dict, domain: str, recs: list[DnsRecord], log: LogFn) -> None:
    auth = {"apikey": creds["key"], "secretapikey": creds["secret"]}
    _, existing = http_json("POST", f"https://api.porkbun.com/api/json/v3/dns/retrieve/{domain}", body=auth)
    have = existing.get("records") or [] if isinstance(existing, dict) else []
    for r in recs:
        name = r.host
        if any(
            x.get("type") == r.type
            and (x.get("name") or "").rstrip(".") in (f"{name}.{domain}" if name else domain, name, domain)
            and str(x.get("content") or "") in (r.value, r.value.rstrip("."))
            for x in have
        ):
            log(f"  Porkbun already has {r.type} {display_host(r.host)}")
            continue
        body = {**auth, "name": name, "type": r.type, "content": r.value, "ttl": "300"}
        if r.priority is not None:
            body["prio"] = str(r.priority)
        http_json("POST", f"https://api.porkbun.com/api/json/v3/dns/create/{domain}", body=body)
        log(f"  Porkbun added {r.type} {display_host(r.host)}")


def _mailcow_already(result: object) -> bool:
    blob = json.dumps(result).lower() if not isinstance(result, str) else result.lower()
    return any(x in blob for x in ("exists", "already", "duplicate", "object_exists"))


def _mailcow_failed(result: object) -> object | None:
    rows = result if isinstance(result, list) else [result] if isinstance(result, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("type") or "").lower() in ("error", "danger"):
            return row
    return None


def add_mailcow(env: dict[str, str], domain: str, local: str, password: str, log: LogFn) -> None:
    log("Creating Mailcow domain…")
    result = mailcow(
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
    failed = _mailcow_failed(result)
    if failed:
        if _mailcow_already(result):
            log("Domain already in Mailcow — continuing.")
        else:
            raise RuntimeError(f"Mailcow domain: {result}")
    log(f"Creating mailbox {local}@{domain}…")
    result = mailcow(
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
    failed = _mailcow_failed(result)
    if failed:
        if _mailcow_already(result):
            log("Mailbox already in Mailcow — continuing.")
        else:
            raise RuntimeError(f"Mailcow mailbox: {result}")


def add_acs(
    env: dict[str, str],
    domain: str,
    locals_: list[str],
    mail_host: str,
    provider: str,
    creds: dict,
    log: LogFn,
    wait: bool = False,
) -> list[DnsRecord]:
    if not env.get("AZURE_SUBSCRIPTION_ID"):
        raise RuntimeError("AZURE_SUBSCRIPTION_ID is missing.")
    _email_id, acs_id, dom_id, managed = acs_paths(env, domain)

    log("Creating Azure send domain…")
    az(
        env,
        "PUT",
        dom_id,
        API_EMAIL,
        {"location": "global", "properties": {"domainManagement": "CustomerManaged"}},
    )
    log("Waiting until Azure publishes SPF/DKIM values (domain is Accepted until then)…")
    obj = wait_acs_domain(env, dom_id, log)
    acs_rows = dns_rows(obj, domain)
    recs = mail_records(domain, mail_host, acs_rows)
    if not records_ready(obj):
        log("Azure has not published DNS values yet. Wait a minute and Add domain again.")
        log_dns(recs, log)
        return recs
    log_dns(recs, log)
    apply_dns(provider, creds, domain, recs, log)
    log("Add those rows at the DNS provider, then click Verify on this site.")
    if wait:
        verify_acs(env, domain, locals_, log)
    return recs


def attach_send_state(env: dict[str, str], domain: str, locals_: list[str], log: LogFn) -> dict:
    """Read-only after Add. Never start Azure checks — that is the Verify button."""
    st: dict[str, str] = {}
    linked = False
    if not azure_ready(env):
        return {"verify_status": st, "verified": False, "send_ready": False, "linked": False}
    try:
        st = verification_status(env, domain)
    except Exception as exc:  # noqa: BLE001
        log(f"Azure status: {exc}")
        return {"verify_status": {}, "verified": False, "send_ready": False, "linked": False}
    try:
        linked = domain_linked(env, domain)
    except Exception:  # noqa: BLE001
        linked = False
    send_ok = can_link_domain(st) and linked
    if send_ok:
        log("Azure send is already linked. You do not need to add those DNS rows again.")
        return {"verify_status": st, "verified": True, "send_ready": True, "linked": True}
    log("Add those rows at the DNS provider, then click Verify. Azure is not checked until then.")
    return {"verify_status": {}, "verified": False, "send_ready": False, "linked": False}


def provision(
    env: dict[str, str],
    domain: str,
    local: str,
    password: str,
    provider: str,
    log: LogFn,
    skip_mailcow: bool = False,
    skip_acs: bool = False,
) -> dict:
    domain = domain.lower().strip().rstrip(".")
    local = local.strip() or "hi"
    password = password or (os.urandom(9).hex() + "Aa1")
    mail_host = env.get("MAIL_HOSTNAME") or "mail.seethinajayadileep.dev"
    store = load_providers()
    creds = dict(store.get(provider) or {})
    if provider == "namecom" and not provider_connected(creds):
        creds = {"user": env.get("NAMECOM_USER") or "", "token": env.get("NAMECOM_TOKEN") or ""}
    recs: list[DnsRecord] = mail_records(domain, mail_host, [])
    azure_needed = False
    if not skip_mailcow:
        add_mailcow(env, domain, local, password, log)
    if skip_acs:
        log_dns(recs, log)
    elif not azure_ready(env):
        azure_needed = True
        log("Azure Setup is empty — send SPF/DKIM will appear after you paste the Entra JSON.")
        log_dns(recs, log)
    else:
        recs = add_acs(env, domain, [local], mail_host, provider, creds, log, wait=False)
    send_state = (
        attach_send_state(env, domain, [local], log) if azure_ready(env) and not skip_acs else {}
    )
    result = {
        "ok": True,
        "domain": domain,
        "email": f"{local}@{domain}",
        "password": password,
        "webmail": f"https://{mail_host}/",
        "imap": f"{mail_host}:993",
        "smtp": f"{mail_host}:587",
        "records": format_records(recs),
        "provider": provider,
        "azure_needed": azure_needed,
        "local_part": local,
        **send_state,
    }
    save_domain(result)
    return result
