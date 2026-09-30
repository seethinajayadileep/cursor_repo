#!/usr/bin/env bash
# Run on the mail VM as root.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
install -d /etc/azure-mail /usr/local/lib/azure-mail/web /usr/local/lib/azure-mail
install -m 644 "$SRC/vm/lib_brand.py" /usr/local/lib/azure-mail/lib_brand.py
install -m 755 "$SRC/vm/add_brand.py" /usr/local/lib/azure-mail/add_brand.py
install -m 755 "$SRC/vm/add-brand" /usr/local/sbin/add-brand
cp -a "$SRC/web/." /usr/local/lib/azure-mail/web/
python3 -m pip install -q -r /usr/local/lib/azure-mail/web/requirements.txt
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
  if [[ ! -f "$MC/docker-compose.override.yml" ]]; then
    install -m 644 "$SRC/web/docker-compose.override.yml" "$MC/docker-compose.override.yml"
  fi
  (cd "$MC" && docker compose up -d nginx-mailcow && docker compose restart nginx-mailcow)
fi
echo
echo "Panel: https://mail.seethinajayadileep.dev/brands/"
echo "Sign in with WEB_ADMIN_PASSWORD or the Mailcow API key from /etc/azure-mail/brand.env"
