#!/usr/bin/env bash
# Publish docs/wiki/*.md to the GitHub Wiki.
# Prerequisite: create the wiki once in the GitHub UI (Create the first page → Save),
# then run:  bash scripts/publish-wiki.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/docs/wiki"
TMP="${TMPDIR:-/tmp}/inkbound-wiki-publish"
REMOTE="https://github.com/nirmal5307/pdf-to-epub-formater.wiki.git"

rm -rf "$TMP"
if ! git clone "$REMOTE" "$TMP" 2>/tmp/inkbound-wiki-clone.err; then
  echo "Wiki git repo not found yet."
  echo "Open https://github.com/nirmal5307/pdf-to-epub-formater/wiki/_new"
  echo "Create a page titled Home, paste docs/wiki/Home.md, Save — then re-run this script."
  cat /tmp/inkbound-wiki-clone.err
  exit 1
fi

cp "$SRC"/*.md "$TMP"/
cd "$TMP"
git add *.md
if git diff --cached --quiet; then
  echo "Wiki already up to date."
  exit 0
fi
git -c user.name='Nirmal Raj' -c user.email='nirmal5307@gmail.com' commit -m "Update Inkbound wiki guides."
git push origin HEAD
echo "Wiki published → https://github.com/nirmal5307/pdf-to-epub-formater/wiki"
