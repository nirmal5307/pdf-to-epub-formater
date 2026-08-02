#!/usr/bin/env bash
# Create / refresh the Inkbound GitHub Project board from existing issues.
# Requires: gh auth refresh -s project,read:project
set -euo pipefail
OWNER=nirmal5307
REPO=pdf-to-epub-formater
TITLE="Inkbound Roadmap"

# Create project (ignore if you prefer to reuse — we always create then link)
JSON=$(gh project create --owner "$OWNER" --title "$TITLE" --format json)
PROJECT_NUMBER=$(echo "$JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["number"])')
PROJECT_ID=$(echo "$JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "Created project #$PROJECT_NUMBER id=$PROJECT_ID"

gh project link "$PROJECT_NUMBER" --owner "$OWNER" --repo "$OWNER/$REPO"

# Status field + options
FIELDS=$(gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json)
STATUS_FIELD=$(echo "$FIELDS" | python3 -c '
import sys,json
d=json.load(sys.stdin)
fields=d["fields"] if isinstance(d,dict) and "fields" in d else d
for f in fields:
  if f.get("name")=="Status":
    print(f["id"]); break
')
DONE_OPT=$(echo "$FIELDS" | python3 -c '
import sys,json
d=json.load(sys.stdin)
fields=d["fields"] if isinstance(d,dict) and "fields" in d else d
for f in fields:
  if f.get("name")=="Status":
    for o in f.get("options",[]):
      if o.get("name") in ("Done","done"):
        print(o["id"]); break
')
TODO_OPT=$(echo "$FIELDS" | python3 -c '
import sys,json
d=json.load(sys.stdin)
fields=d["fields"] if isinstance(d,dict) and "fields" in d else d
for f in fields:
  if f.get("name")=="Status":
    for o in f.get("options",[]):
      if o.get("name") in ("Todo","To do","To Do"):
        print(o["id"]); break
')

echo "Status field=$STATUS_FIELD done=$DONE_OPT todo=$TODO_OPT"

add_issue() {
  local num=$1
  local status_opt=$2
  ITEM_JSON=$(gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "https://github.com/$OWNER/$REPO/issues/$num" --format json)
  ITEM_ID=$(echo "$ITEM_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
  if [[ -n "$STATUS_FIELD" && -n "$status_opt" ]]; then
    gh project item-edit --project-id "$PROJECT_ID" --id "$ITEM_ID" --field-id "$STATUS_FIELD" --single-select-option-id "$status_opt" >/dev/null
  fi
  echo "added #$num -> $status_opt"
}

# Closed = Done
for n in 1 2 3 4 5 6 7 8 9; do
  add_issue "$n" "$DONE_OPT"
done
# Open = Todo
for n in 10 11 12 13 14 15 16 17; do
  add_issue "$n" "$TODO_OPT"
done

echo "Board: https://github.com/users/$OWNER/projects/$PROJECT_NUMBER"
echo "Also linked from: https://github.com/$OWNER/$REPO/projects"
