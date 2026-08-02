#!/usr/bin/env bash
# Install runtime deps inside the Codespace / devcontainer.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ Installing Python packages…"
python -m pip install --upgrade pip
pip install -r requirements.txt

if command -v apt-get >/dev/null 2>&1; then
  echo "→ Installing Tesseract (OCR)…"
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tesseract-ocr
fi

echo "→ Codespace setup complete."
