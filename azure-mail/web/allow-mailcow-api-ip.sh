#!/usr/bin/env bash
# Allow the panel (Docker gateway 172.22.1.1) to call the Mailcow API.
# Run on the mail VM as root. Does not restart Mailcow.
set -euo pipefail
MC="${MC:-/opt/mailcow-dockerized}"
cd "$MC"
set -a
# shellcheck disable=SC1091
. ./mailcow.conf
set +a
ALLOW='127.0.0.1,4.224.47.183,172.22.1.1,172.22.1.0/24,172.16.0.0/12'
docker compose exec -T mysql-mailcow mysql -u"${DBUSER}" -p"${DBPASS}" "${DBNAME}" \
  -e "UPDATE api SET allow_from='${ALLOW}' WHERE access='rw' AND active=1; SELECT access, allow_from FROM api;"
echo "Mailcow API allow_from now includes 172.22.1.1 (panel on the host)."
