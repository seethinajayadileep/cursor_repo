#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

npm run build -w @interviewpilot/desktop

export CSC_IDENTITY_AUTO_DISCOVERY=false
cd apps/desktop

# Portable via electron-builder (no Wine required for portable on many setups)
npx electron-builder --win portable --x64 -c.win.signAndEditExecutable=false || true

# NSIS Setup via system makensis (works on Linux without Wine)
if command -v makensis >/dev/null 2>&1; then
  makensis installer.nsi
fi

echo "Artifacts:"
ls -lh release/*.{exe,zip} 2>/dev/null || ls -lh release/
