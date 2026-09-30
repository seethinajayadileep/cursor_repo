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

python3 - <<'PY' > /tmp/acs-dns.txt
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
PY

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

failed_status() {
  case "$1" in
    VerificationFailed|Failed|Canceled|Cancelled) return 0 ;;
    *) return 1 ;;
  esac
}

link_and_mailfrom() {
  # GET current list, then append. Replacing the list unlinks every other brand.
  ACS_ID="$ACS_ID" API_ACS="$API_ACS" DOM_ID="$DOM_ID" MANAGED_ID="$MANAGED_ID" python3 -c '
import json, os, subprocess
acs_id = os.environ["ACS_ID"]
api = os.environ["API_ACS"]
dom_id = os.environ["DOM_ID"]
managed = os.environ["MANAGED_ID"]
raw = subprocess.check_output(["az", "rest", "--method", "get", "--uri", f"{acs_id}?api-version={api}"])
cur = json.loads(raw)
linked = list((cur.get("properties") or {}).get("linkedDomains") or [])
changed = False
for extra in (managed, dom_id):
    if extra not in linked:
        linked.append(extra)
        changed = True
if changed:
    body = json.dumps({"properties": {"linkedDomains": linked}})
    subprocess.check_call(["az", "rest", "--method", "patch", "--uri", f"{acs_id}?api-version={api}", "--body", body])
    print("Linked domain for Azure send (GET+append, keeps other domains).")
else:
    print("Already linked.")
print("LINKED:")
for item in linked:
    print("  " + item)
'
  for user in "${MAILFROMS[@]}"; do
    echo "  MailFrom ${user}@${DOMAIN}"
    if ! az rest --method put \
      --uri "${DOM_ID}/senderUsernames/${user}?api-version=${API_EMAIL}" \
      --body "{\"properties\":{\"username\":\"${user}\",\"displayName\":\"${user}\"}}" \
      >/tmp/acs-from.json 2>/tmp/acs-from.err; then
      echo "  MailFrom ${user} failed (quota is often 1 = DoNotReply)."
      echo "  Portal: mail-box -> ${DOMAIN} -> MailFrom -> rename DoNotReply to ${user}"
      echo "  or: cat /tmp/acs-from.err"
    fi
  done
}

for kind in Domain SPF DKIM DKIM2; do
  verify "$kind"
done

echo "Polling verification (up to ~10 min). Linking as soon as Domain is Verified…"
ok=0
linked=0
for i in $(seq 1 20); do
  d="$(status_of Domain)"; s="$(status_of SPF)"; k="$(status_of DKIM)"; k2="$(status_of DKIM2)"
  echo "  [$i] Domain=$d SPF=$s DKIM=$k DKIM2=$k2"
  if [[ "$d" == "Verified" && "$linked" != 1 ]]; then
    link_and_mailfrom
    linked=1
  fi
  if [[ "$d" == "Verified" && "$s" == "Verified" && "$k" == "Verified" && "$k2" == "Verified" ]]; then
    ok=1
    break
  fi
  for pair in "Domain:$d" "SPF:$s" "DKIM:$k" "DKIM2:$k2"; do
    kind="${pair%%:*}"
    st="${pair#*:}"
    if failed_status "$st"; then
      echo "  ${kind} failed (${st}) — DNS may have been added late. Retrying."
      verify "$kind"
    fi
  done
  sleep 30
done

if [[ "$linked" != 1 ]]; then
  echo
  echo "Domain TXT is not Verified yet. Gmail will bounce 501 5.1.7 until it is."
  echo "Wait until the Domain TXT is public, then re-run:"
  echo "  $0 $DOMAIN ${MAILFROMS[*]}"
  exit 1
fi

if [[ "$ok" != 1 ]]; then
  echo
  echo "Send is linked. Some SPF/DKIM checks are still pending — re-run to finish:"
  echo "  $0 $DOMAIN ${MAILFROMS[*]}"
fi

echo
echo "Mailcow (once): admin UI -> Domains -> add ${DOMAIN} -> Add domain AND restart SOGo"
echo "                -> Mailboxes -> ${MAILFROMS[0]}@${DOMAIN}"
echo "Then webmail: https://${MAIL_HOST}/  as ${MAILFROMS[0]}@${DOMAIN}"
echo "Done. No Azure portal needed next time — re-run this script."
