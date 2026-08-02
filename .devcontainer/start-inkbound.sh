#!/usr/bin/env bash
# Start Inkbound in the background when a Codespace / devcontainer starts.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${INKBOUND_PORT:-8765}"
LOG="${TMPDIR:-/tmp}/inkbound.log"

if command -v ss >/dev/null 2>&1 && ss -ltn "( sport = :${PORT} )" 2>/dev/null | grep -q ":${PORT}"; then
  echo "Inkbound already listening on :${PORT}"
  exit 0
fi
if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Inkbound already listening on :${PORT}"
  exit 0
fi

echo "→ Starting Inkbound on ${INKBOUND_HOST:-0.0.0.0}:${PORT}…"
nohup python -m app.main >"${LOG}" 2>&1 &
echo $! >"${TMPDIR:-/tmp}/inkbound.pid"

# Wait briefly so port forward / browser open sees a live server
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${PORT}/api/capabilities" >/dev/null 2>&1; then
    echo "Inkbound is ready → port ${PORT} (log: ${LOG})"
    exit 0
  fi
  sleep 0.4
done

echo "Inkbound may still be starting — check ${LOG}"
exit 0
