#!/usr/bin/env bash
# Run from a checkout of this repo:
#   /opt/cursor_repo/azure-mail/web/install-web.sh
# If this folder is missing on the mail VM, use bootstrap.sh instead.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
if [[ ! -f "$SRC/vm/lib_brand.py" ]]; then
  echo "This is not a full azure-mail checkout ($SRC/vm/lib_brand.py missing)."
  echo "On the mail VM run:"
  echo "  curl -fsSL https://raw.githubusercontent.com/seethinajayadileep/cursor_repo/cursor/azure-mail-acs-relay-9a02/azure-mail/web/bootstrap.sh | sudo bash"
  exit 1
fi
install -d /etc/azure-mail /usr/local/lib/azure-mail/web /usr/local/lib/azure-mail
install -m 644 "$SRC/vm/lib_brand.py" /usr/local/lib/azure-mail/lib_brand.py
install -m 755 "$SRC/vm/add_brand.py" /usr/local/lib/azure-mail/add_brand.py
install -m 755 "$SRC/vm/add-brand" /usr/local/sbin/add-brand
cp -a "$SRC/web/." /usr/local/lib/azure-mail/web/
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq python3-venv python3-pip
VENV=/usr/local/lib/azure-mail/venv
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -r /usr/local/lib/azure-mail/web/requirements.txt
if [[ ! -f /etc/azure-mail/brand.env ]]; then
  install -m 600 "$SRC/vm/brand.env.example" /etc/azure-mail/brand.env
fi
if [[ ! -f /etc/azure-mail/providers.json ]]; then
  echo '{}' >/etc/azure-mail/providers.json
  chmod 600 /etc/azure-mail/providers.json
fi
install -m 644 "$SRC/web/azure-mail-web.service" /etc/systemd/system/azure-mail-web.service
systemctl daemon-reload
systemctl enable --now azure-mail-web
MC=/opt/mailcow-dockerized
if [[ -d "$MC" ]]; then
  install -m 644 "$SRC/web/nginx-brands.conf" "$MC/data/conf/nginx/site.mailbox.custom"
  install -m 644 "$SRC/web/mailbox-sso.php" "$MC/data/web/mailbox-sso.php"
  PYTHONPATH=/usr/local/lib/azure-mail AZURE_MAIL_ENV=/etc/azure-mail/brand.env \
    /usr/local/lib/azure-mail/venv/bin/python -c 'from lib_brand import persist_sso_secret; persist_sso_secret()'
  # Reload nginx only. Never compose down / restart the stack (that 502s Mailcow).
  docker compose -f "$MC/docker-compose.yml" --env-file "$MC/mailcow.conf" \
    exec -T nginx-mailcow nginx -s reload || true
  bash "$SRC/web/allow-mailcow-api-ip.sh" || true
fi
echo
echo "Panel: https://mail.seethinajayadileep.dev/brands/"
echo "Admin only: WEB_ADMIN_PASSWORD in /etc/azure-mail/brand.env"
echo "Mailbox users sign in at https://mail.seethinajayadileep.dev/ — they cannot open this panel."
