#!/usr/bin/env bash
# install.sh — install share-session auto-sync launchd job on macOS.
#
# What it does:
#   1. Verify deps (git, gh logged in, python3)
#   2. Ensure ~/.claude/share-session/{config.json, auto-config.json} exist
#      (interactively prompts for missing fields)
#   3. mkdir ~/.claude/share-session/.logs
#   4. Generate ~/Library/LaunchAgents/com.openwhispr.share-session.plist
#      from platform/launchd-template.plist (envsubst $HOME)
#   5. launchctl load the plist (idempotent)
#
# Idempotent: safe to re-run. Pass --force to overwrite existing plist
# without prompting.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${HOME}/.claude/share-session"
LOG_DIR="${STATE_DIR}/.logs"
CONFIG_FILE="${STATE_DIR}/config.json"
AUTO_CONFIG_FILE="${STATE_DIR}/auto-config.json"
PLIST_LABEL="com.openwhispr.share-session"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"
TEMPLATE="${SKILL_DIR}/platform/launchd-template.plist"
AUTO_CONFIG_TEMPLATE="${SKILL_DIR}/defaults/auto-config.template.json"

FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

log()  { printf '\033[36m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[install]\033[0m %s\n' "$*"; }
err()  { printf '\033[31m[install]\033[0m %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }

# ---------- 1. deps ----------
log "checking dependencies..."
command -v git     >/dev/null || die "git not found"
command -v gh      >/dev/null || die "gh CLI not found (brew install gh)"
command -v python3 >/dev/null || die "python3 not found"
command -v envsubst >/dev/null || die "envsubst not found (brew install gettext)"
gh auth status >/dev/null 2>&1 || die "gh not logged in — run: gh auth login"

GH_USER_DEFAULT="$(gh api user --jq .login 2>/dev/null || echo "")"

# ---------- 2. base config.json (shared with manual mode) ----------
mkdir -p "$STATE_DIR" "$LOG_DIR"
if [[ ! -f "$CONFIG_FILE" ]]; then
  log "no ${CONFIG_FILE} yet — let's create it."
  read -r -p "Team repo (https URL, e.g. https://github.com/<you>/team-conversations.git): " repo_url
  read -r -p "Your GitHub username [${GH_USER_DEFAULT}]: " gh_user
  gh_user="${gh_user:-$GH_USER_DEFAULT}"
  [[ -z "$repo_url" || -z "$gh_user" ]] && die "repoUrl and githubUser are required"
  cat > "$CONFIG_FILE" <<EOF
{
  "repoUrl": "${repo_url}",
  "githubUser": "${gh_user}",
  "defaultProject": "",
  "autoOpenPr": true
}
EOF
  log "saved $CONFIG_FILE"
else
  log "config.json exists, leaving as-is"
fi

# ---------- 3. auto-config.json ----------
if [[ ! -f "$AUTO_CONFIG_FILE" ]]; then
  log "no ${AUTO_CONFIG_FILE} yet — bootstrapping from template."
  cp "$AUTO_CONFIG_TEMPLATE" "$AUTO_CONFIG_FILE"

  echo
  echo "Auto-sync is opt-in by project. List the project names (basename of cwd) you want auto-sync for."
  echo "Examples: VoxEdit  my-cool-project  another-project"
  echo "Leave blank to set up later (auto-sync will stay idle until you add at least one)."
  read -r -p "Projects to allow (space-separated): " allow_input
  if [[ -n "$allow_input" ]]; then
    python3 -c "
import json, sys
path = sys.argv[1]
projects = sys.argv[2].split()
cfg = json.load(open(path))
cfg['allowProjects'] = projects
json.dump(cfg, open(path, 'w'), indent=2, ensure_ascii=False)
" "$AUTO_CONFIG_FILE" "$allow_input"
    log "allowProjects = ${allow_input}"
  else
    warn "allowProjects is empty — auto-sync is effectively disabled until you edit ${AUTO_CONFIG_FILE}"
  fi
else
  log "auto-config.json exists, leaving as-is"
fi

# ---------- 4. ensure log dir + plist ----------
log "preparing log dir at ${LOG_DIR}"
mkdir -p "$LOG_DIR"

if [[ -f "$PLIST_PATH" && "$FORCE" != "1" ]]; then
  warn "plist already exists at $PLIST_PATH"
  read -r -p "overwrite & reload? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || die "aborted"
fi

log "rendering plist..."
HOME="$HOME" envsubst < "$TEMPLATE" > "$PLIST_PATH"
log "wrote $PLIST_PATH"

# ---------- 5. launchctl load ----------
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
log "launchctl loaded ${PLIST_LABEL}"

# ---------- summary ----------
cat <<EOF

✓ Installed.

Next scan: within $(python3 -c "import json; print(json.load(open('${AUTO_CONFIG_FILE}')).get('scanIntervalMinutes', 5))") minute(s).
Log:     ${LOG_DIR}/auto.log
Errors:  ${LOG_DIR}/auto.err.log
Status:  launchctl list | grep ${PLIST_LABEL}
Disable: bash ${SKILL_DIR}/uninstall.sh

Config:  ${AUTO_CONFIG_FILE}
  - idleMinutes:   how long a JSONL must be untouched before push
  - minUserTurns:  threshold of real user turns to push
  - allowProjects: ONLY these projects auto-sync
  - blockSessionIds: skip specific sessions forever

To trigger a manual scan right now:
  python3 ${SKILL_DIR}/auto_scanner.py --dry-run    # preview
  python3 ${SKILL_DIR}/auto_scanner.py              # real

EOF
