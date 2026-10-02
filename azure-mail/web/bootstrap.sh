#!/usr/bin/env bash
# Run on the mail VM from any directory (you do not already have azure-mail/ there):
#   curl -fsSL https://raw.githubusercontent.com/seethinajayadileep/cursor_repo/cursor/azure-mail-acs-relay-9a02/azure-mail/web/bootstrap.sh | sudo bash
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/seethinajayadileep/cursor_repo.git}"
BRANCH="${BRANCH:-cursor/azure-mail-acs-relay-9a02}"
DEST="${DEST:-/opt/cursor_repo}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3 python3-pip python3-venv ca-certificates
if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" fetch --depth 1 origin "$BRANCH"
  git -C "$DEST" checkout "$BRANCH"
  git -C "$DEST" pull --ff-only origin "$BRANCH" || git -C "$DEST" reset --hard "origin/$BRANCH"
else
  rm -rf "$DEST"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$DEST"
fi
chmod +x "$DEST/azure-mail/web/install-web.sh"
exec "$DEST/azure-mail/web/install-web.sh"
