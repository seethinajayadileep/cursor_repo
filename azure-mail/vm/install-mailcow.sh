#!/usr/bin/env bash
# Run on the Azure Ubuntu VM as root (or via sudo).
# Env required: MAILCOW_HOSTNAME (FQDN like mail.example.com)
# Optional: ACS_SMTP_USERNAME ACS_SMTP_PASSWORD MAILCOW_TZ SKIP_LETS_ENCRYPT
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash install-mailcow.sh"
  exit 1
fi

MAILCOW_HOSTNAME="${MAILCOW_HOSTNAME:?Set MAILCOW_HOSTNAME=mail.yourdomain.com}"
MAILCOW_TZ="${MAILCOW_TZ:-UTC}"
SKIP_LETS_ENCRYPT="${SKIP_LETS_ENCRYPT:-y}"
INSTALL_DIR=/opt/mailcow-dockerized

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git curl ca-certificates gnupg lsb-release jq python3 python3-venv \
  apt-transport-https software-properties-common fail2ban unattended-upgrades

# Swap so Mailcow does not OOM on 8 GB
if [[ ! -f /swapfile ]]; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

hostnamectl set-hostname "$MAILCOW_HOSTNAME"
if ! grep -q "$MAILCOW_HOSTNAME" /etc/hosts; then
  echo "127.0.1.1 $MAILCOW_HOSTNAME" >> /etc/hosts
fi

# Docker
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

# Azure VMs often have broken IPv6; Mailcow then prompts. Force IPv4.
sysctl -w net.ipv6.conf.all.disable_ipv6=1 >/dev/null || true
sysctl -w net.ipv6.conf.default.disable_ipv6=1 >/dev/null || true

if [[ ! -d $INSTALL_DIR ]]; then
  git clone https://github.com/mailcow/mailcow-dockerized "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
ln -sfn mailcow.conf .env

if [[ ! -f mailcow.conf ]]; then
  export MAILCOW_HOSTNAME
  export MAILCOW_TZ
  export SKIP_CLAMD=y
  export MAILCOW_BRANCH=master
  export ENABLE_IPV6=false
  ./generate_config.sh
fi

# 8 GB VM: skip ClamAV + FTS. Azure cannot send on :25 so we relay via ACS.
sed -i 's/^SKIP_CLAMD=.*/SKIP_CLAMD=y/' mailcow.conf
sed -i 's/^SKIP_FTS=.*/SKIP_FTS=y/' mailcow.conf || true
if grep -q '^SKIP_LETS_ENCRYPT=' mailcow.conf; then
  sed -i "s/^SKIP_LETS_ENCRYPT=.*/SKIP_LETS_ENCRYPT=${SKIP_LETS_ENCRYPT}/" mailcow.conf
else
  echo "SKIP_LETS_ENCRYPT=${SKIP_LETS_ENCRYPT}" >> mailcow.conf
fi

# ACS SMTP relay — Azure blocks outbound port 25; this is the send path
mkdir -p data/conf/postfix
cat > data/conf/postfix/extra.cf <<'EOF'
# Azure Communication Services SMTP relay (port 587). Do not send via MX/port 25.
relayhost = [smtp.azurecomm.net]:587
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = texthash:/opt/postfix/conf/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_sasl_tls_security_options = noanonymous
smtp_tls_security_level = encrypt
smtp_tls_wrappermode = no
EOF

if [[ -n "${ACS_SMTP_USERNAME:-}" && -n "${ACS_SMTP_PASSWORD:-}" ]]; then
  printf '[smtp.azurecomm.net]:587 %s:%s\n' "$ACS_SMTP_USERNAME" "$ACS_SMTP_PASSWORD" \
    > data/conf/postfix/sasl_passwd
  chmod 600 data/conf/postfix/sasl_passwd
else
  echo "WARNING: ACS_SMTP_USERNAME/PASSWORD not set. Fill $INSTALL_DIR/data/conf/postfix/sasl_passwd then restart postfix."
  echo '[smtp.azurecomm.net]:587 REPLACE_USERNAME:REPLACE_PASSWORD' > data/conf/postfix/sasl_passwd
  chmod 600 data/conf/postfix/sasl_passwd
fi

COMPOSE=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
fi

"${COMPOSE[@]}" pull
"${COMPOSE[@]}" up -d

echo
echo "============================================================"
echo "Mailcow is starting. Wait ~2 minutes then open:"
echo "  https://$MAILCOW_HOSTNAME"
echo "  or https://$(curl -4 -s ifconfig.me || true)"
echo
echo "Admin login (CHANGE IMMEDIATELY):"
echo "  user: admin"
echo "  pass: moohoo"
echo
echo "Then: Configuration -> Mail setup -> Domains -> add domain"
echo "      Mailboxes -> create hello@domain"
echo "      Catch-all optional"
echo
echo "From-address MUST be an ACS-verified domain (Azure managed"
echo "  xxx.azurecomm.net or your custom domain after DNS verify)."
echo "============================================================"
