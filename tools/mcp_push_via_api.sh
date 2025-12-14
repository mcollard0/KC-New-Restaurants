#!/usr/bin/env bash
set -euo pipefail;

usage() { echo "Usage: $0 [--branch BRANCH] [--message MSG] [--dry-run]"; };

BRANCH=$(git rev-parse --abbrev-ref HEAD);
MESSAGE="MCP test: sync from local working copy on $(date -I)";
DRYRUN=0;

# Parse args first so --dry-run works without token
while [[ ${1:-} ]]; do
  case "$1" in
    --branch) BRANCH="$2"; shift 2;;
    --message) MESSAGE="$2"; shift 2;;
    --dry-run) DRYRUN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 2;;
  esac;
done;

if (( DRYRUN == 0 )) && [[ -z "${GITHUB_MCP_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_MCP_TOKEN is not set. Export it before running (or use --dry-run).";
  exit 1;
fi;

remote_url=$(git remote get-url origin);
# Parse owner/repo from SSH or HTTPS URL
case "$remote_url" in
  git@github.com:*) owner_repo=${remote_url#git@github.com:}; owner_repo=${owner_repo%.git};;
  https://github.com/*) owner_repo=${remote_url#https://github.com/}; owner_repo=${owner_repo%.git};;
  *) echo "Unsupported remote URL: $remote_url"; exit 2;;
esac;
OWNER=${owner_repo%%/*}; REPO=${owner_repo##*/};

echo "Repo: $OWNER/$REPO on branch $BRANCH";

# Build list of changed/untracked files
mapfile -d '' FILES < <(git ls-files -m -o --exclude-standard -z);
if (( ${#FILES[@]} == 0 )); then echo "No changes to push."; exit 0; fi;

DATEISO=$(date -I);

backup_one() {
  local p="$1";
  mkdir -p "backups/$(dirname "$p")";
  cp -f -- "$p" "backups/$p.$DATEISO" || true;
  local count=0;
  for f in $(ls -t backups/"$p".* 2>/dev/null || true); do
    count=$((count+1));
    if (( count > 50 )); then rm -f -- "$f"; fi;
  done;
}

urlencode() { python3 - "$1" <<'PY'
import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))
PY
};

for p in "${FILES[@]}"; do
  [[ -z "$p" ]] && continue;
  [[ "$p" == .git/* ]] && continue;
  echo "--- $p";
  backup_one "$p";
  if (( DRYRUN )); then
    echo "[dry-run] would PUT $p to GitHub via contents API with message: $MESSAGE";
    continue;
  fi;
  URLPATH=$(urlencode "$p");
  CONTENT=$(base64 -w 0 -- "$p");
  SHA="";
  STATUS=$(curl -sS -o /tmp/gh_content.json -w "%{http_code}" -H "Authorization: Bearer $GITHUB_MCP_TOKEN" -H "Accept: application/vnd.github+json" "https://api.github.com/repos/$OWNER/$REPO/contents/$URLPATH?ref=$BRANCH") || STATUS=$?;
  if [[ "$STATUS" == "200" ]]; then
    SHA=$(jq -r .sha < /tmp/gh_content.json);
  fi;
  if [[ -n "$SHA" && "$SHA" != "null" ]]; then
    jq -n --arg msg "$MESSAGE" --arg content "$CONTENT" --arg branch "$BRANCH" --arg sha "$SHA" '{message:$msg, content:$content, branch:$branch, sha:$sha}' > /tmp/put.json;
  else
    jq -n --arg msg "$MESSAGE" --arg content "$CONTENT" --arg branch "$BRANCH" '{message:$msg, content:$content, branch:$branch}' > /tmp/put.json;
  fi;
  PUT_STATUS=$(curl -sS -o /tmp/put_resp.json -w "%{http_code}" -X PUT -H "Authorization: Bearer $GITHUB_MCP_TOKEN" -H "Accept: application/vnd.github+json" -d @/tmp/put.json "https://api.github.com/repos/$OWNER/$REPO/contents/$URLPATH");
  if [[ "$PUT_STATUS" != "200" && "$PUT_STATUS" != "201" ]]; then
    echo "ERROR pushing $p (status $PUT_STATUS):";
    jq -r .message < /tmp/put_resp.json || cat /tmp/put_resp.json || true;
    exit 3;
  else
    sha=$(jq -r '.commit.sha' < /tmp/put_resp.json);
    echo "OK $p -> commit $sha";
  fi;
done;

echo "Done.";