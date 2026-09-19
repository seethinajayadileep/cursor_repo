#!/usr/bin/env bash
# Lightweight API e2e smoke (no paid APIs)
set -euo pipefail
API="${API_URL:-http://localhost:8787}"

curl -sf "$API/api/health" >/dev/null
TOKEN=$(curl -sf -X POST "$API/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"demo@interviewpilot.ai","password":"demo12345"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

auth() { curl -sf -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' "$@"; }

auth -X POST "$API/api/ai/detect-question" -d '{"text":"What is normalization in SQL?"}' | grep -q technical
auth -X POST "$API/api/ai/answer" -d '{"question":"Tell me about yourself.","category":"hr"}' | grep -q concise
auth -X POST "$API/api/sessions" -d '{"sessionType":"mock_interview","jobRole":"Data Analyst"}' | grep -q session
auth -X POST "$API/api/mock/start" -d '{"role":"Data Analyst"}' | grep -q question
auth "$API/api/documents" | grep -q documents
auth "$API/api/diagnostics" | grep -q demoMode

echo "E2E API smoke passed"
