#!/usr/bin/env python3
"""Send one test message through Azure Communication Services SMTP (port 587)."""
from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True, help="Gmail or other inbox you can open")
    parser.add_argument("--from-addr", default="", help="Must be ACS-verified (DoNotReply@xxx.azurecomm.net or custom)")
    parser.add_argument("--env", default=str(Path(__file__).resolve().parent / ".env"))
    args = parser.parse_args()

    env = {**load_env(Path(args.env)), **os.environ}
    host = env.get("ACS_SMTP_HOST", "smtp.azurecomm.net")
    port = int(env.get("ACS_SMTP_PORT", "587"))
    user = env.get("ACS_SMTP_USERNAME", "")
    password = env.get("ACS_SMTP_PASSWORD", "")
    managed = env.get("AZURE_MANAGED_FROM_DOMAIN", "")
    from_addr = args.from_addr or (f"DoNotReply@{managed}" if managed else "")

    if not user or not password or not from_addr:
        print("Missing ACS_SMTP_USERNAME / ACS_SMTP_PASSWORD / from address.", file=sys.stderr)
        print("Run deploy.sh first or pass --from-addr.", file=sys.stderr)
        return 2

    msg = EmailMessage()
    msg["Subject"] = "Azure ACS relay test"
    msg["From"] = from_addr
    msg["To"] = args.to
    msg.set_content(
        "If you received this, Azure Communication Services SMTP works.\n"
        "Mailcow on the VM should send the same way (relayhost :587).\n"
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)

    print(f"Sent via {host}:{port}")
    print(f"From: {from_addr}")
    print(f"To:   {args.to}")
    print("Open the inbox AND spam folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
