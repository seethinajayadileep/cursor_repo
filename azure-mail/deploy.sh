#!/usr/bin/env bash
# Deploy Azure mail fix: VM (receive + webmail) + ACS Email (send relay).
# Requires: Azure CLI logged in to the subscription that has the $1000 credit.
#
# Usage:
#   cd azure-mail
#   MAIL_HOSTNAME=mail.yourdomain.com ./deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p keys out

if ! command -v az >/dev/null 2>&1; then
  echo "Install Azure CLI first: https://aka.ms/installazurecli"
  echo "Then: az login"
  exit 1
fi

SUB_STATE="$(az account show --query '{name:name,id:id,state:state}' -o json 2>/dev/null || true)"
if [[ -z "$SUB_STATE" ]]; then
  echo "Not logged in. Run: az login"
  exit 1
fi
echo "Using subscription:"
echo "$SUB_STATE"

MAIL_HOSTNAME="${MAIL_HOSTNAME:?Set MAIL_HOSTNAME=mail.yourdomain.com (A record FQDN, not the mailbox domain only)}"
RG="${RESOURCE_GROUP:-rg-azure-mail}"
LOCATION="${LOCATION:-centralindia}"
DATA_LOCATION="${DATA_LOCATION:-United States}"
VM_SIZE="${VM_SIZE:-Standard_B2ms}"
ADMIN_USER="${ADMIN_USER:-azureuser}"
KEY_PATH="$ROOT/keys/azure_mail_ed25519"

if [[ ! -f "$KEY_PATH" ]]; then
  ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "azure-mail"
  echo "Created SSH key: $KEY_PATH"
fi
PUBKEY="$(cat "${KEY_PATH}.pub")"

echo
echo "This creates:"
echo "  - Resource group $RG in $LOCATION"
echo "  - Ubuntu 22.04 VM $VM_SIZE (8 GB) with inbound 25/443/993"
echo "  - Azure Communication Services Email (send via smtp.azurecomm.net:587)"
echo "  - Mailcow on the VM, relayed through ACS (Azure blocks outbound :25)"
echo
echo "Credit burn is roughly \$50–80/month for the VM + tiny ACS per email."
if [[ "${NONINTERACTIVE:-}" != "1" ]]; then
  read -r -p "Continue? [y/N] " go
  [[ "$go" =~ ^[Yy]$ ]] || exit 0
fi

az group create --name "$RG" --location "$LOCATION" -o none

echo "Deploying ARM/Bicep (few minutes)..."
az deployment group create \
  --resource-group "$RG" \
  --name mailfix \
  --template-file "$ROOT/infra/main.bicep" \
  --parameters \
    location="$LOCATION" \
    dataLocation="$DATA_LOCATION" \
    adminUsername="$ADMIN_USER" \
    adminPublicKey="$PUBKEY" \
    vmSize="$VM_SIZE" \
  --query properties.outputs -o json | tee "$ROOT/out/outputs.json"

IP="$(az deployment group show -g "$RG" -n mailfix --query properties.outputs.publicIP.value -o tsv)"
PIP_NAME="$(az deployment group show -g "$RG" -n mailfix --query properties.outputs.publicIpName.value -o tsv)"
ACS_NAME="$(az deployment group show -g "$RG" -n mailfix --query properties.outputs.acsName.value -o tsv)"
ACS_ID="$(az deployment group show -g "$RG" -n mailfix --query properties.outputs.acsId.value -o tsv)"
EMAIL_NAME="$(az deployment group show -g "$RG" -n mailfix --query properties.outputs.emailServiceName.value -o tsv)"
DOMAIN_ID="$(az deployment group show -g "$RG" -n mailfix --query properties.outputs.managedDomainId.value -o tsv)"
TENANT="$(az account show --query tenantId -o tsv)"

echo
echo "Public IP: $IP"
echo "Set DNS NOW (grey cloud / DNS only, not proxied):"
echo "  A    mail    $IP"
echo "  so $MAIL_HOSTNAME -> $IP"
echo

# Reverse DNS only works after the A record exists. Try; ignore failure.
az network public-ip update -g "$RG" -n "$PIP_NAME" --reverse-fqdn "${MAIL_HOSTNAME}." -o none 2>/dev/null \
  && echo "PTR set to $MAIL_HOSTNAME" \
  || echo "PTR not set yet. After the A record resolves, run:"$'\n'"  az network public-ip update -g $RG -n $PIP_NAME --reverse-fqdn ${MAIL_HOSTNAME}."

# Link Azure-managed domain to ACS so you can send immediately from *@xxxx.azurecomm.net
echo "Linking Azure managed send domain to ACS..."
az rest --method patch \
  --uri "${ACS_ID}?api-version=2023-06-01" \
  --body "{\"properties\":{\"linkedDomains\":[\"${DOMAIN_ID}\"]}}" \
  >/dev/null || echo "Link via portal if this failed: ACS resource -> Domains -> Connect"

FROM_DOMAIN="$(az communication email domain show \
  --email-service-name "$EMAIL_NAME" \
  --name AzureManagedDomain \
  --resource-group "$RG" \
  --query mailFromSenderDomain -o tsv 2>/dev/null || true)"
if [[ -z "$FROM_DOMAIN" ]]; then
  FROM_DOMAIN="$(az communication email domain show \
    --email-service-name "$EMAIL_NAME" \
    --name AzureManagedDomain \
    --resource-group "$RG" \
    --query properties.fromSenderDomain -o tsv 2>/dev/null || echo 'see portal Email Communication Service > Domains')"
fi

# Entra app for ACS SMTP
echo "Creating Entra app for ACS SMTP..."
APP_NAME="acs-smtp-mail-${RG}"
APP_ID="$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv)"
if [[ -z "$APP_ID" || "$APP_ID" == "null" ]]; then
  APP_ID="$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)"
fi
az ad sp create --id "$APP_ID" >/dev/null 2>&1 || true
SECRET="$(az ad app credential reset --id "$APP_ID" --display-name acs-smtp --query password -o tsv)"
az role assignment create --assignee "$APP_ID" --role "Contributor" --scope "$ACS_ID" -o none 2>/dev/null \
  || az role assignment create --assignee "$APP_ID" --role "Owner" --scope "$ACS_ID" -o none

echo "Waiting 45s for Entra role propagation..."
sleep 45

# SMTP username resource (official ACS SMTP AUTH)
SMTP_USER="mailrelay"
SMTP_CREATED=0
for api in 2025-09-01 2024-09-01-preview 2023-06-01-preview; do
  if az rest --method put \
    --uri "${ACS_ID}/smtpUsernames/${SMTP_USER}?api-version=${api}" \
    --body "{\"properties\":{\"entraApplicationId\":\"${APP_ID}\",\"tenantId\":\"${TENANT}\",\"username\":\"${SMTP_USER}\"}}" \
    >/tmp/acs-smtp-user.json 2>/tmp/acs-smtp-user.err; then
    SMTP_CREATED=1
    break
  fi
done

if [[ "$SMTP_CREATED" -eq 1 ]] && grep -q '"username"' /tmp/acs-smtp-user.json 2>/dev/null; then
  ACS_SMTP_USERNAME="$SMTP_USER"
else
  # Fallback username format used by some ACS SMTP tenants
  ACS_SMTP_USERNAME="${ACS_NAME}.${APP_ID}.${TENANT}"
  echo "SMTP username resource API not available; using fallback username:"
  echo "  $ACS_SMTP_USERNAME"
  cat /tmp/acs-smtp-user.err || true
fi
ACS_SMTP_PASSWORD="$SECRET"

umask 077
cat > "$ROOT/.env" <<EOF
RESOURCE_GROUP=$RG
LOCATION=$LOCATION
PUBLIC_IP=$IP
MAIL_HOSTNAME=$MAIL_HOSTNAME
ADMIN_USER=$ADMIN_USER
SSH_KEY=$KEY_PATH
ACS_NAME=$ACS_NAME
ACS_ID=$ACS_ID
EMAIL_SERVICE_NAME=$EMAIL_NAME
ACS_SMTP_HOST=smtp.azurecomm.net
ACS_SMTP_PORT=587
ACS_SMTP_USERNAME=$ACS_SMTP_USERNAME
ACS_SMTP_PASSWORD=$ACS_SMTP_PASSWORD
ENTRA_APP_ID=$APP_ID
ENTRA_TENANT_ID=$TENANT
AZURE_MANAGED_FROM_DOMAIN=$FROM_DOMAIN
EOF

echo
echo "Wrote credentials to $ROOT/.env  (do not commit this file)"

echo "Waiting for SSH on $IP..."
for i in $(seq 1 36); do
  if ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=8 \
    "${ADMIN_USER}@${IP}" 'echo ssh-ok' >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

echo "Installing Mailcow + ACS relay on the VM..."
scp -i "$KEY_PATH" -o StrictHostKeyChecking=no \
  "$ROOT/vm/install-mailcow.sh" "${ADMIN_USER}@${IP}:/tmp/install-mailcow.sh"

ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no "${ADMIN_USER}@${IP}" \
  "sudo MAILCOW_HOSTNAME='$MAIL_HOSTNAME' \
        ACS_SMTP_USERNAME='$ACS_SMTP_USERNAME' \
        ACS_SMTP_PASSWORD='$ACS_SMTP_PASSWORD' \
        SKIP_LETS_ENCRYPT=y \
        bash /tmp/install-mailcow.sh"

echo
echo "============================================================"
echo "AZURE MAIL FIX is up."
echo
echo "SSH:  ssh -i $KEY_PATH ${ADMIN_USER}@${IP}"
echo "Web:  https://$IP   (admin / moohoo)  CHANGE PASSWORD"
echo
echo "1) DNS for RECEIVE (every mailbox domain):"
echo "     MX   @   $MAIL_HOSTNAME.   priority 10"
echo "     A    mail  $IP     (if not done)"
echo
echo "2) DNS for SEND (ACS custom domain):"
echo "     ./add-send-domain.sh yourdomain.com hi"
echo "     (prints TXT/SPF/DKIM, verifies, links mailboxCs, adds MailFrom hi@)"
echo
echo "3) Immediate SEND TEST (Azure managed domain):"
echo "     From:  DoNotReply@${FROM_DOMAIN}"
echo "     python3 $ROOT/test_acs_send.py --to you@gmail.com"
echo
echo "4) After Mailcow has a mailbox, send from webmail. Receive:"
echo "     Gmail -> hello@yourdomain.com -> Mailcow inbox"
echo
echo "Outbound port 25 from this VM will ALWAYS fail. That is Azure."
echo "Sending goes ACS :587. Receiving comes in on :25. That is the fix."
echo "============================================================"
