#!/usr/bin/env bash
# Add a mailbox domain for ACS send without clicking the Azure portal.
# Receive/mailboxes stay in Mailcow. This only does Azure Email + link + MailFrom.
#
# Usage (Cloud Shell or any PC with Azure CLI):
#   az login
#   ./add-send-domain.sh example.com
#   ./add-send-domain.sh example.com hi hello support
#
# Extra args after the domain are MailFrom local-parts (hi -> hi@example.com).
# Default MailFrom is "hi" if you pass none.
set -euo pipefail

DOMAIN="${1:?Usage: $0 example.com [mailfrom ...]}"
shift || true
if [[ $# -eq 0 ]]; then
  MAILFROMS=(hi)
else
  MAILFROMS=("$@")
fi

RG="${RESOURCE_GROUP:-mailboxRg}"
ACS_NAME="${ACS_NAME:-mailboxCs}"
EMAIL_NAME="${EMAIL_NAME:-mail-box}"
MAIL_HOST="${MAIL_HOSTNAME:-mail.seethinajayadileep.dev}"
API_EMAIL="${API_EMAIL:-2023-03-31}"
API_ACS="${API_ACS:-2025-09-01}"

az config set extension.use_dynamic_install=yes_without_prompt >/dev/null 2>&1 || true

SUB="$(az account show --query id -o tsv)"
ACS_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Communication/CommunicationServices/${ACS_NAME}"
EMAIL_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Communication/emailServices/${EMAIL_NAME}"
DOM_ID="${EMAIL_ID}/domains/${DOMAIN}"
MANAGED_ID="${EMAIL_ID}/domains/AzureManagedDomain"

echo "Subscription: $SUB"
echo "Domain:       $DOMAIN"
echo "MailFroms:    ${MAILFROMS[*]}@$DOMAIN"
echo "Mailcow MX:   $MAIL_HOST"
echo

export DOMAIN
echo "Creating ACS custom domain if missing..."
az rest --method put \
  --uri "${DOM_ID}?api-version=${API_EMAIL}" \
  --body '{"location":"global","properties":{"domainManagement":"CustomerManaged"}}' \
  >/tmp/acs-domain.json

python3 - <<PY
import json, os
domain = os.environ["DOMAIN"]
d = json.load(open("/tmp/acs-domain.json"))
vr = (d.get("properties") or {}).get("verificationRecords") or {}
def rec(kind):
    x = vr.get(kind) or {}
    t = x.get("type") or ("CNAME" if kind.startswith("DKIM") else "TXT")
    name = x.get("name") or "@"
    val = x.get("value") or ""
    suffix = "." + domain
    if name.endswith(suffix):
        name = name[: -len(suffix)]
    if name in ("", "@", domain):
        name = "@"
    print(f"{kind}|{t}|{name}|{val}")
for k in ("Domain", "SPF", "DKIM", "DKIM2"):
    rec(k)
PY > /tmp/acs-dns.txt

echo
echo "========== DNS to add on ${DOMAIN} (Name.com / Cloudflare grey-cloud) =========="
echo
echo "RECEIVE (Mailcow — skip if already set):"
printf "  %-6s %-55s %s\n" "MX" "@" "${MAIL_HOST}.   (priority 10)"
echo
echo "SEND (ACS):"
while IFS='|' read -r kind typ name val; do
  [[ -z "$kind" ]] && continue
  host="$name"
  # Name.com appends the zone. Use @ for apex TXT.
  if [[ "$name" == "$DOMAIN" || "$name" == "@" ]]; then
    host="@"
  fi
  printf "  %-6s %-55s %s\n" "$typ" "$host" "$val"
done < /tmp/acs-dns.txt
echo
echo "SPF host must be @ (not ${DOMAIN}.${DOMAIN})."
echo "Do not CNAME the bare domain. Grey-cloud / DNS-only."
echo "============================================================================="
echo

if [[ -t 0 && "${NONINTERACTIVE:-}" != "1" ]]; then
  read -r -p "Press Enter after those DNS records exist (or wait 5–15 min)..."
fi

verify() {
  local kind="$1"
  echo "Verify ${kind}..."
  az rest --method post \
    --uri "${DOM_ID}/initiateVerification?api-version=${API_EMAIL}" \
    --body "{\"verificationType\":\"${kind}\"}" \
    >/dev/null || true
}

status_of() {
  local kind="$1"
  az rest --method get --uri "${DOM_ID}?api-version=${API_EMAIL}" -o json \
    | python3 -c "import json,sys; d=json.load(sys.stdin);
vs=(d.get('properties') or {}).get('verificationStates') or {};
print((vs.get(sys.argv[1]) or {}).get('status') or 'Unknown')" "$kind"
}

for kind in Domain SPF DKIM DKIM2; do
  verify "$kind"
done

echo "Polling verification (up to ~10 min)..."
ok=0
for i in $(seq 1 20); do
  d="$(status_of Domain)"; s="$(status_of SPF)"; k="$(status_of DKIM)"; k2="$(status_of DKIM2)"
  echo "  [$i] Domain=$d SPF=$s DKIM=$k DKIM2=$k2"
  if [[ "$d" == "Verified" && "$s" == "Verified" && "$k" == "Verified" && "$k2" == "Verified" ]]; then
    ok=1
    break
  fi
  sleep 30
done

if [[ "$ok" != 1 ]]; then
  echo
  echo "Still not all Verified. Fix DNS (especially apex SPF TXT), wait, re-run:"
  echo "  $0 $DOMAIN ${MAILFROMS[*]}"
  exit 1
fi

echo "Linking domain to ${ACS_NAME} (keep Azure-managed domain too)..."
az rest --method patch \
  --uri "${ACS_ID}?api-version=${API_ACS}" \
  --body "{\"properties\":{\"linkedDomains\":[\"${MANAGED_ID}\",\"${DOM_ID}\"]}}" \
  >/dev/null

echo "LINKED:"
az rest --method get --uri "${ACS_ID}?api-version=${API_ACS}" --query properties.linkedDomains -o tsv

echo "Adding MailFrom usernames..."
for user in "${MAILFROMS[@]}"; do
  echo "  ${user}@${DOMAIN}"
  if ! az rest --method put \
    --uri "${DOM_ID}/senderUsernames/${user}?api-version=${API_EMAIL}" \
    --body "{\"properties\":{\"username\":\"${user}\",\"displayName\":\"${user}\"}}" \
    >/tmp/acs-from.json 2>/tmp/acs-from.err; then
    echo "  MailFrom ${user} failed (quota is often 1 = DoNotReply)."
    echo "  Portal: mail-box -> ${DOMAIN} -> MailFrom -> rename DoNotReply to ${user}"
    echo "  or: cat /tmp/acs-from.err"
  fi
done

echo
echo "Mailcow (once): admin UI -> Domains -> add ${DOMAIN} -> Add domain AND restart SOGo"
echo "                -> Mailboxes -> ${MAILFROMS[0]}@${DOMAIN}"
echo "Then webmail: https://${MAIL_HOST}/  as ${MAILFROMS[0]}@${DOMAIN}"
echo "Done. No Azure portal needed next time — re-run this script."
