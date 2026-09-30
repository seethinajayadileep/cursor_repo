"""Shared Azure + Mailcow + multi-registrar DNS helpers."""
from __future__ import annotations

import json
import os
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


def dns_rows(domain_obj: dict, domain: str) -> list[DnsRecord]:
    vr = (domain_obj.get("properties") or {}).get("verificationRecords") or {}
    rows: list[DnsRecord] = []
    for kind in ("Domain", "SPF", "DKIM", "DKIM2"):
        x = vr.get(kind) or {}
        typ = x.get("type") or ("CNAME" if kind.startswith("DKIM") else "TXT")
        name = apex_host(x.get("name") or "", domain)
        val = x.get("value") or ""
        rows.append(DnsRecord(type=typ, host=name, value=val, kind=kind))
    return rows


def mail_records(domain: str, mail_host: str, acs_rows: list[DnsRecord]) -> list[DnsRecord]:
    mx = DnsRecord(type="MX", host="", value=mail_host.rstrip(".") + ".", priority=10, kind="MX")
    return [mx, *acs_rows]


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
    if isinstance(result, dict) and str(result.get("type") or "").lower() == "error":
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
    if isinstance(result, dict) and str(result.get("type") or "").lower() == "error":
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
    wait: bool = True,
) -> list[DnsRecord]:
    sub = env.get("AZURE_SUBSCRIPTION_ID") or ""
    rg = env.get("RESOURCE_GROUP") or "mailboxRg"
    email = env.get("EMAIL_NAME") or "mail-box"
    acs = env.get("ACS_NAME") or "mailboxCs"
    if not sub:
        raise RuntimeError("AZURE_SUBSCRIPTION_ID is missing.")
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

    log("Creating Azure send domain…")
    obj = az(
        env,
        "PUT",
        dom_id,
        API_EMAIL,
        {"location": "global", "properties": {"domainManagement": "CustomerManaged"}},
    )
    acs_rows = dns_rows(obj if isinstance(obj, dict) else {}, domain)
    recs = mail_records(domain, mail_host, acs_rows)
    apply_dns(provider, creds, domain, recs, log)

    for kind in ("Domain", "SPF", "DKIM", "DKIM2"):
        try:
            az(env, "POST", f"{dom_id}/initiateVerification", API_EMAIL, {"verificationType": kind})
        except RuntimeError as e:
            log(f"  initiate {kind}: {e}")

    def status(kind: str) -> str:
        d = az(env, "GET", dom_id, API_EMAIL)
        vs = (d.get("properties") or {}).get("verificationStates") or {}
        return (vs.get(kind) or {}).get("status") or "Unknown"

    if wait:
        log("Waiting for Azure Verified (up to 10 min)…")
        ok = False
        for i in range(1, 21):
            st = {k: status(k) for k in ("Domain", "SPF", "DKIM", "DKIM2")}
            log(f"  [{i}] {st}")
            if all(v == "Verified" for v in st.values()):
                ok = True
                break
            time.sleep(30)
        if not ok:
            raise RuntimeError(
                "DNS not verified yet. Check the registrar records (apex SPF on @) and run again."
            )
        log("Linking domain to Azure Communication Services…")
        cur = az(env, "GET", acs_id, API_ACS)
        linked = list((cur.get("properties") or {}).get("linkedDomains") or [])
        for extra in (managed, dom_id):
            if extra not in linked:
                linked.append(extra)
        az(env, "PATCH", acs_id, API_ACS, {"properties": {"linkedDomains": linked}})
        log("Adding MailFrom senders…")
        for user in locals_:
            try:
                az(
                    env,
                    "PUT",
                    f"{dom_id}/senderUsernames/{user}",
                    API_EMAIL,
                    {"properties": {"username": user, "displayName": user}},
                )
                log(f"  {user}@{domain}")
            except RuntimeError as e:
                log(f"  {user}@{domain} failed (MailFrom quota is often 1 / DoNotReply): {e}")
    return recs


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
    recs: list[DnsRecord] = []
    if not skip_mailcow:
        add_mailcow(env, domain, local, password, log)
    if not skip_acs:
        recs = add_acs(env, domain, [local], mail_host, provider, creds, log)
    return {
        "ok": True,
        "domain": domain,
        "email": f"{local}@{domain}",
        "password": password,
        "webmail": f"https://{mail_host}/",
        "imap": f"{mail_host}:993",
        "smtp": f"{mail_host}:587",
        "records": format_records(recs),
        "provider": provider,
    }
