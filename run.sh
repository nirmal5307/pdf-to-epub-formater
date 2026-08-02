#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PORT=8765
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use."
  echo "Inkbound may already be running → http://127.0.0.1:$PORT"
  echo "To free the port:  kill \$(lsof -tiTCP:$PORT -sTCP:LISTEN)"
  exit 1
fi

echo "Inkbound → http://127.0.0.1:$PORT"
exec python -m app.main
