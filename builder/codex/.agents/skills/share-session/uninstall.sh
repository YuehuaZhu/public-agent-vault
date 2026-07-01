#!/usr/bin/env bash
# uninstall.sh — remove share-session auto-sync launchd job.
#
# Does NOT delete:
#   - ~/.claude/share-session/config.json   (manual mode still works)
#   - ~/.claude/share-session/auto-state.json
#   - ~/.claude/share-session/.logs/
#   - ~/.claude/share-session/repo/         (cloned team repo)
#
# Pass --purge to also remove all the above (full reset).

set -euo pipefail

STATE_DIR="${HOME}/.claude/share-session"
PLIST_LABEL="com.openwhispr.share-session"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"

PURGE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge) PURGE=1; shift ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

log()  { printf '\033[36m[uninstall]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[uninstall]\033[0m %s\n' "$*"; }

if [[ -f "$PLIST_PATH" ]]; then
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
  rm -f "$PLIST_PATH"
  log "removed launchd plist: $PLIST_PATH"
else
  warn "no plist at $PLIST_PATH (already uninstalled?)"
fi

if [[ "$PURGE" == "1" ]]; then
  warn "--purge: removing ${STATE_DIR}"
  rm -rf "$STATE_DIR"
  log "purged state directory"
else
  cat <<EOF

✓ Uninstalled launchd job. Manual share-session (+share-session) still works.

State preserved at ${STATE_DIR} (config, logs, cloned repo).
Run with --purge to wipe everything: bash uninstall.sh --purge
EOF
fi
