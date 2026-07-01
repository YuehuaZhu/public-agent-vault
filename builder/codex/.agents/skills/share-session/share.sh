#!/usr/bin/env bash
# share-session: bundle current Claude Code transcript + memory and push to team repo as a PR.
#
# Manual mode:
#   share.sh --title "客户需求-acme 第一次会" [--session <uuid>] [--project <name>] [--dry-run]
#
# Auto mode (called by auto_scanner.py):
#   share.sh --auto --session <uuid> --project <name> [--title <fallback>]
#
# Reads config from ~/.claude/share-session/config.json (created interactively on first run).

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${HOME}/.claude/share-session"
CONFIG_FILE="${STATE_DIR}/config.json"
RULES_FILE="${STATE_DIR}/redaction-rules.json"
BLOCKLIST_FILE="${STATE_DIR}/blocklist.txt"
REPO_DIR="${STATE_DIR}/repo"
PENDING_DIR="${STATE_DIR}/pending"
PROJECTS_ROOT="${HOME}/.claude/projects"

# ---------- args ----------
TITLE=""
SESSION=""
PROJECT_OVERRIDE=""
DRY_RUN=0
AUTO=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="$2"; shift 2 ;;
    --session) SESSION="$2"; shift 2 ;;
    --project) PROJECT_OVERRIDE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --auto) AUTO=1; shift ;;
    -h|--help)
      sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

log() { printf '\033[36m[share-session]\033[0m %s\n' "$*" >&2; }
err() { printf '\033[31m[share-session]\033[0m %s\n' "$*" >&2; }

# Auto mode requires --session and --project (scanner always passes them)
if [[ "$AUTO" == "1" ]]; then
  if [[ -z "$SESSION" || -z "$PROJECT_OVERRIDE" ]]; then
    err "--auto mode requires --session and --project"
    exit 1
  fi
else
  if [[ -z "$TITLE" ]]; then
    err "--title required in manual mode"
    exit 1
  fi
fi

# ---------- first-run setup (manual mode only) ----------
mkdir -p "$STATE_DIR" "$PENDING_DIR"

if [[ ! -f "$RULES_FILE" ]]; then
  cp "${SKILL_DIR}/defaults/redaction-rules.json" "$RULES_FILE"
  log "installed default redaction-rules.json to $RULES_FILE"
fi
if [[ ! -f "$BLOCKLIST_FILE" ]]; then
  : > "$BLOCKLIST_FILE"
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  if [[ "$AUTO" == "1" ]]; then
    err "config.json missing — auto mode cannot prompt. Run install.sh or manual share.sh first."
    exit 1
  fi
  log "first run — creating $CONFIG_FILE"
  default_user="$(gh api user --jq .login 2>/dev/null || echo "")"
  read -r -p "Team repo (https URL, e.g. https://github.com/<you>/team-conversations.git): " repo_url
  read -r -p "Your GitHub username [${default_user}]: " gh_user
  gh_user="${gh_user:-$default_user}"
  if [[ -z "$repo_url" || -z "$gh_user" ]]; then
    err "repoUrl and githubUser are required"; exit 1
  fi
  cat > "$CONFIG_FILE" <<EOF
{
  "repoUrl": "${repo_url}",
  "githubUser": "${gh_user}",
  "defaultProject": "",
  "autoOpenPr": true
}
EOF
  log "saved $CONFIG_FILE"
fi

# ---------- read config ----------
REPO_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['repoUrl'])")
GH_USER=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['githubUser'])")
AUTO_PR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('autoOpenPr', True))")

# ---------- project / session detection ----------
if [[ "$AUTO" == "1" ]]; then
  PROJECT_NAME="$PROJECT_OVERRIDE"
  CWD="(scanner)"
  # Session UUIDs are NOT globally unique across project dirs (Claude Code
  # may mirror the same session under multiple project dirs). Pick the one
  # whose JSONL's `cwd` field has basename == --project. Fall back to first.
  JSONL_PATH="$(python3 -c "
import json, sys, glob, os
from pathlib import Path
session, project = sys.argv[1], sys.argv[2]
candidates = glob.glob(str(Path.home() / '.claude' / 'projects' / '*' / f'{session}.jsonl'))
chosen = None
for c in candidates:
    try:
        with open(c, encoding='utf-8') as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                cwd = d.get('cwd')
                if cwd and os.path.basename(cwd) == project:
                    chosen = c; break
        if chosen: break
    except Exception:
        pass
print(chosen or (candidates[0] if candidates else ''))
" "$SESSION" "$PROJECT_NAME")"
  if [[ -z "$JSONL_PATH" ]]; then
    err "session JSONL not found for ${SESSION} under ${PROJECTS_ROOT}"
    exit 1
  fi
  PROJECT_TRANSCRIPT_DIR="$(dirname "$JSONL_PATH")"
else
  CWD="$(pwd)"
  PROJECT_NAME="${PROJECT_OVERRIDE:-$(basename "$CWD")}"
  ENCODED_PROJECT_PATH="$(echo "$CWD" | sed 's|/|-|g')"
  PROJECT_TRANSCRIPT_DIR="${HOME}/.claude/projects/${ENCODED_PROJECT_PATH}"

  if [[ ! -d "$PROJECT_TRANSCRIPT_DIR" ]]; then
    err "no transcript dir for cwd: $PROJECT_TRANSCRIPT_DIR"
    err "are you running this from a directory where you've used Claude Code?"
    exit 1
  fi

  if [[ -n "$SESSION" ]]; then
    JSONL_PATH="${PROJECT_TRANSCRIPT_DIR}/${SESSION}.jsonl"
  elif [[ -n "${CLAUDE_SESSION_ID:-}" ]]; then
    JSONL_PATH="${PROJECT_TRANSCRIPT_DIR}/${CLAUDE_SESSION_ID}.jsonl"
  else
    JSONL_PATH="$(ls -t "${PROJECT_TRANSCRIPT_DIR}"/*.jsonl 2>/dev/null | head -1)"
  fi

  if [[ ! -f "$JSONL_PATH" ]]; then
    err "session JSONL not found: $JSONL_PATH"
    err "available sessions in $PROJECT_TRANSCRIPT_DIR:"
    ls -t "$PROJECT_TRANSCRIPT_DIR"/*.jsonl 2>/dev/null | head -5 >&2 || true
    exit 1
  fi
fi

SESSION_ID="$(basename "$JSONL_PATH" .jsonl)"
log "using session: $JSONL_PATH"

# ---------- title fallback for auto ----------
if [[ "$AUTO" == "1" && -z "$TITLE" ]]; then
  # Try ai-title from JSONL; else fallback to short uuid + date
  AI_TITLE="$(python3 -c "
import json, sys
for line in open(sys.argv[1], encoding='utf-8'):
    try:
        d = json.loads(line)
        if d.get('type') == 'ai-title' and d.get('aiTitle'):
            print(d['aiTitle']); break
    except: pass
" "$JSONL_PATH")"
  TITLE="${AI_TITLE:-auto-share ${SESSION_ID:0:8} $(date +%Y-%m-%d)}"
fi

# ---------- branch / dir naming ----------
if [[ "$AUTO" == "1" ]]; then
  DIR_NAME="auto/${SESSION_ID}"
  BRANCH_NAME="auto/${SESSION_ID}"
else
  SLUG="$(python3 -c "
import re, sys
s = sys.argv[1].lower()
s = re.sub(r'[^a-z0-9一-鿿]+', '-', s)
s = s.strip('-')
print(s[:80])
" "$TITLE")"
  DATE_PART="$(date +%Y-%m-%d-%H%M)"
  DIR_NAME="${DATE_PART}-${SLUG}"
  BRANCH_NAME="shares/${DATE_PART}-${SLUG}"
fi

# ---------- workspace ----------
TMP_DIR="$(mktemp -d -t share-session.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
log "workspace: $TMP_DIR"

# redact JSONL
log "redacting JSONL..."
python3 "${SKILL_DIR}/redactor.py" \
  --rules "$RULES_FILE" \
  --blocklist "$BLOCKLIST_FILE" \
  < "$JSONL_PATH" > "${TMP_DIR}/session.jsonl"

# render markdown from REDACTED jsonl
log "rendering markdown..."
python3 "${SKILL_DIR}/renderer.py" \
  --input "${TMP_DIR}/session.jsonl" \
  --output "${TMP_DIR}/conversation.md" \
  --title "$TITLE" \
  --sharer "@${GH_USER}" \
  --project "$PROJECT_NAME"

# snapshot memory dir (redacted)
MEMORY_SRC="${PROJECT_TRANSCRIPT_DIR}/memory"
if [[ -d "$MEMORY_SRC" ]]; then
  log "snapshotting memory..."
  mkdir -p "${TMP_DIR}/memory-snapshot"
  for f in "$MEMORY_SRC"/*.md; do
    [[ -e "$f" ]] || continue
    python3 "${SKILL_DIR}/redactor.py" \
      --rules "$RULES_FILE" \
      --blocklist "$BLOCKLIST_FILE" \
      --text "$(cat "$f")" > "${TMP_DIR}/memory-snapshot/$(basename "$f")"
  done
else
  log "no memory/ dir to snapshot"
fi

# meta.json
ISO_NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TURNS="$(python3 -c "
import json,sys
n=0
for line in open('${TMP_DIR}/session.jsonl'):
    try:
        d=json.loads(line)
        if d.get('type')=='user':
            msg=d.get('message') or {}
            c=msg.get('content')
            if isinstance(c,list) and any(isinstance(b,dict) and b.get('type')=='text' for b in c):
                n+=1
    except: pass
print(n)")"
MODE_LABEL="manual"
[[ "$AUTO" == "1" ]] && MODE_LABEL="auto"
cat > "${TMP_DIR}/meta.json" <<EOF
{
  "title": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$TITLE"),
  "mode": "${MODE_LABEL}",
  "sessionId": "${SESSION_ID}",
  "sharer": "${GH_USER}",
  "project": "${PROJECT_NAME}",
  "originalCwd": "${CWD}",
  "sharedAt": "${ISO_NOW}",
  "userTurns": ${TURNS}
}
EOF

if [[ "$DRY_RUN" == "1" ]]; then
  log "DRY RUN — artifacts in $TMP_DIR"
  log "  session.jsonl ($(wc -l < "${TMP_DIR}/session.jsonl") lines)"
  log "  conversation.md ($(wc -l < "${TMP_DIR}/conversation.md") lines)"
  ls -la "${TMP_DIR}/" >&2
  KEEP_DIR="${PENDING_DIR}/dryrun-${DIR_NAME//\//-}"
  rm -rf "$KEEP_DIR"; mkdir -p "$KEEP_DIR"
  cp -R "${TMP_DIR}/." "$KEEP_DIR/"
  log "preserved at: $KEEP_DIR"
  trap - EXIT
  exit 0
fi

# ---------- git pipeline ----------
if [[ ! -d "$REPO_DIR/.git" ]]; then
  log "cloning $REPO_URL → $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"
git fetch origin --quiet
git checkout main --quiet
git pull --rebase --quiet origin main

if [[ "$AUTO" == "1" ]]; then
  # Fixed branch + force-push (overwrite same session's PR content)
  TARGET="projects/${GH_USER}/${PROJECT_NAME}/auto/${SESSION_ID}"
  log "target dir: $TARGET"
  log "branch: $BRANCH_NAME (auto, force-with-lease)"

  if git show-ref --verify --quiet "refs/remotes/origin/${BRANCH_NAME}"; then
    git checkout -B "$BRANCH_NAME" "origin/${BRANCH_NAME}" --quiet
  else
    git checkout -B "$BRANCH_NAME" --quiet
  fi

  # Clean any stale content under the target dir, then write fresh
  rm -rf "$TARGET"
  mkdir -p "$TARGET"
  cp "${TMP_DIR}/session.jsonl" "$TARGET/"
  cp "${TMP_DIR}/conversation.md" "$TARGET/"
  cp "${TMP_DIR}/meta.json" "$TARGET/"
  if [[ -d "${TMP_DIR}/memory-snapshot" ]]; then
    cp -R "${TMP_DIR}/memory-snapshot" "$TARGET/"
  fi

  git add "$TARGET"
  if git diff --cached --quiet; then
    log "no changes to commit (content unchanged); skipping push"
    # Still emit the existing PR URL so the scanner can record it
    existing_pr_num="$(gh pr list --head "$BRANCH_NAME" --state open --json number --jq '.[0].number' 2>/dev/null || echo "")"
    if [[ -n "$existing_pr_num" ]]; then
      repo_slug="$(python3 -c "
import json,re
url=json.load(open('$CONFIG_FILE'))['repoUrl']
m=re.search(r'github\.com[:/]([^/]+/[^/.]+)',url); print(m.group(1) if m else '')")"
      [[ -n "$repo_slug" ]] && echo "https://github.com/${repo_slug}/pull/${existing_pr_num}"
    fi
    exit 0
  fi
  git commit -m "auto-share: ${TITLE}

session: ${SESSION_ID}
project: ${PROJECT_NAME}
sharer: @${GH_USER}
mode: auto (refreshed at ${ISO_NOW})" --quiet

  log "force-pushing branch..."
  if ! git push -u origin "$BRANCH_NAME" --force-with-lease --quiet; then
    err "push failed — leaving local branch in place"
    exit 1
  fi

  # PR: create only if not already open
  existing_pr="$(gh pr list --head "$BRANCH_NAME" --state open --json number --jq '.[0].number' 2>/dev/null || echo "")"
  if [[ -z "$existing_pr" ]]; then
    log "no existing open PR — creating one..."
    PR_BODY_FILE="${TMP_DIR}/pr-body.md"
    {
      echo "## Auto-synced"
      echo ""
      echo "This PR is automatically refreshed when this Claude Code session is idle for ≥30 minutes."
      echo "Each refresh force-pushes the branch \`${BRANCH_NAME}\` and updates this PR in place."
      echo ""
      echo "Close this PR if you don't want it auto-updated; the scanner will not re-open it."
      echo ""
      echo "---"
      echo ""
      echo "## Latest preview"
      echo ""
      head -20 "${TMP_DIR}/conversation.md"
      echo ""
      echo "_Full conversation: \`${TARGET}/conversation.md\`_"
    } > "$PR_BODY_FILE"
    PR_URL="$(gh pr create \
      --title "auto-share: ${TITLE}" \
      --body-file "$PR_BODY_FILE" \
      --base main \
      --head "$BRANCH_NAME" 2>&1)"
    echo "$PR_URL"
  else
    log "existing PR #${existing_pr} — force-push refreshed it in place"
    echo "https://github.com/$(python3 -c "
import json,re
url=json.load(open('$CONFIG_FILE'))['repoUrl']
m=re.search(r'github\.com[:/]([^/]+/[^/.]+)',url); print(m.group(1) if m else '')")/pull/${existing_pr}"
  fi

  log "done (auto)."
else
  # Manual mode: unique branch + new PR each time
  TARGET="projects/${GH_USER}/${PROJECT_NAME}/${DIR_NAME}"
  suffix=""
  n=2
  while [[ -d "${TARGET}${suffix}" ]] || git show-ref --verify --quiet "refs/remotes/origin/${BRANCH_NAME}${suffix}"; do
    suffix="-${n}"; n=$((n+1))
  done
  TARGET="${TARGET}${suffix}"
  BRANCH_NAME="${BRANCH_NAME}${suffix}"

  log "target dir: $TARGET"
  log "branch: $BRANCH_NAME"

  git checkout -b "$BRANCH_NAME" --quiet

  mkdir -p "$TARGET"
  cp "${TMP_DIR}/session.jsonl" "$TARGET/"
  cp "${TMP_DIR}/conversation.md" "$TARGET/"
  cp "${TMP_DIR}/meta.json" "$TARGET/"
  if [[ -d "${TMP_DIR}/memory-snapshot" ]]; then
    cp -R "${TMP_DIR}/memory-snapshot" "$TARGET/"
  fi

  git add "$TARGET"
  git commit -m "share: ${TITLE}

session: ${SESSION_ID}
project: ${PROJECT_NAME}
sharer: @${GH_USER}" --quiet

  log "pushing branch..."
  if ! git push -u origin "$BRANCH_NAME" --quiet; then
    err "push failed — stashing artifacts to $PENDING_DIR/$DIR_NAME"
    KEEP_DIR="${PENDING_DIR}/${DIR_NAME}"
    mkdir -p "$KEEP_DIR"
    cp -R "${TMP_DIR}/." "$KEEP_DIR/"
    exit 1
  fi

  if [[ "$AUTO_PR" == "True" || "$AUTO_PR" == "true" ]]; then
    log "creating PR..."
    PR_BODY_FILE="${TMP_DIR}/pr-body.md"
    {
      echo "## TL;DR"
      echo ""
      head -20 "${TMP_DIR}/conversation.md"
      echo ""
      echo "---"
      echo "_Full conversation: \`${TARGET}/conversation.md\`_"
    } > "$PR_BODY_FILE"

    PR_URL="$(gh pr create \
      --title "share: ${TITLE}" \
      --body-file "$PR_BODY_FILE" \
      --base main \
      --head "$BRANCH_NAME" 2>&1)"
    echo "$PR_URL"
  fi

  log "done."
fi
