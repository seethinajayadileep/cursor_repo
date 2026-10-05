#!/usr/bin/env bash
# Prove Azure's port-25 send block vs ACS :587 send, from your laptop or the VM.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && set -a && source "$ROOT/.env" && set +a

echo "== 1) Outbound port 25 to Gmail (Azure VM: expected BLOCKED) =="
if timeout 8 bash -c 'echo >/dev/tcp/gmail-smtp-in.l.google.com/25' 2>/dev/null; then
  echo "PORT25_OPEN — this subscription can send like Hostinger. Rare on credits."
else
  echo "PORT25_BLOCKED — normal on Azure credit. Do not try to 'open' it."
fi

echo
echo "== 2) ACS SMTP 587 (expected OPEN) =="
if timeout 8 bash -c 'echo >/dev/tcp/smtp.azurecomm.net/587' 2>/dev/null; then
  echo "ACS_587_OPEN — send path is available."
else
  echo "ACS_587_CLOSED — check internet / firewall."
fi

echo
echo "== 3) Inbound 25 on the mail VM (receive) =="
if [[ -n "${PUBLIC_IP:-}" ]]; then
  if timeout 8 bash -c "echo >/dev/tcp/${PUBLIC_IP}/25" 2>/dev/null; then
    echo "INBOUND_25_OPEN on $PUBLIC_IP — MX can deliver to Mailcow."
  else
    echo "INBOUND_25_CLOSED on $PUBLIC_IP — wait for Mailcow, or NSG/DNS not ready."
  fi
else
  echo "No PUBLIC_IP in .env; run from azure-mail after deploy.sh"
fi

echo
echo "== 4) Optional authenticated ACS send =="
if [[ -n "${ACS_SMTP_USERNAME:-}" && -n "${1:-}" ]]; then
  python3 "$ROOT/test_acs_send.py" --to "$1"
else
  echo "To send a real test:  python3 $ROOT/test_acs_send.py --to you@gmail.com"
fi
