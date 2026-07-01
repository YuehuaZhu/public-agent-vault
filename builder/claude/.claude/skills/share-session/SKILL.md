---
name: share-session
description: Use when the user wants to share the current Claude Code conversation with their team — pushes the transcript (redacted), a rendered markdown view, and a memory snapshot to a private team GitHub repo, opens a PR. Triggers: "+share-session", "/share-session", "把这次对话分享给团队", "share this session", "share conversation". Skip for: routine local commits, code reviews, or anything not intended for cross-machine team visibility.
---

# Share Session

Bundle the current Claude Code transcript + memory snapshot and push it as a Pull Request to the team `team-conversations` repo.

## When to use

The user says one of:

- `+share-session "<title>"` (e.g. `+share-session "客户需求-acme 第一次会"`)
- `/share-session "<title>"`
- "share this session", "把这次对话分享给团队", "推到 team-conversations"

## How it works

1. Detect the current session's JSONL transcript in `~/.claude/projects/<encoded-cwd>/`
2. Run a regex redactor (API keys, Tokens, Bearer, emails, plus user blocklist) over the JSONL
3. Render the redacted JSONL into a readable `conversation.md` (tool calls folded into `<details>`)
4. Snapshot the project memory directory (also redacted)
5. Commit to a `shares/<date>-<slug>` branch and open a PR on the team repo

Target layout in the team repo:

```
projects/<github-user>/<project>/<YYYY-MM-DD-HHMM-slug>/
├── session.jsonl
├── conversation.md
├── memory-snapshot/
└── meta.json
```

## Running it

```bash
bash ~/.claude/skills/share-session/share.sh --title "客户需求-acme 第一次会"
```

Optional flags:
- `--session <uuid>`: explicitly pick a session (default: the most recently modified JSONL for the current cwd)
- `--project <name>`: override project name in the path (default: basename of cwd)
- `--dry-run`: produce artifacts in `~/.claude/share-session/pending/dryrun-*/` without pushing

## First run

On first invocation the script will:
1. Copy default redaction rules into `~/.claude/share-session/redaction-rules.json`
2. Create an empty `~/.claude/share-session/blocklist.txt` (add custom secret words here, one per line)
3. Prompt for the team repo URL and your GitHub username, save to `~/.claude/share-session/config.json`

## What gets redacted

Defaults (configurable in `~/.claude/share-session/redaction-rules.json`):
- OpenAI / Anthropic / GitHub / Google / AWS API keys
- `Bearer <token>` headers
- Email addresses
- Custom strings in `~/.claude/share-session/blocklist.txt`

**Not** redacted: customer / company names, product names, file paths, business details. The intended audience is your trusted internal team (4–10 people). If you need to share with customers, add their names to the blocklist or wait for the V2 review-gate flow.

## What to tell the user after sharing

Print the PR URL. The user can then `@`-mention teammates in the PR or copy the link into Slack.

## Failure handling

- **Network failure during push**: artifacts saved to `~/.claude/share-session/pending/<slug>/` for manual retry
- **Missing config / SSH key**: skill explains exactly what to fix; does not silently fail
- **Malformed JSONL lines**: skipped and noted in `conversation.md` (does not abort)

## Auto-sync mode (V1.5)

In addition to the explicit `+share-session` command, share-session also has an **opt-in automatic mode** driven by a macOS launchd job. When enabled and configured:

- Every 5 min a tiny scanner (`auto_scanner.py`) checks `~/.claude/projects/*/*.jsonl`
- A session is auto-pushed only if **all** of these are true:
  - Project is listed in `~/.claude/share-session/auto-config.json::allowProjects`
  - The JSONL has been idle for ≥ `idleMinutes` (default 30)
  - The session has ≥ `minUserTurns` real user inputs (default 20; skill injections / system reminders / tool results are not counted)
  - The session is not in `blockSessionIds`
  - The user has not manually closed an earlier auto PR for this session
- Each session has a fixed branch `auto/<session-uuid>` and a fixed directory `projects/<user>/<project>/auto/<session-uuid>/`. Re-pushes are force-pushes to the same branch, so the same PR updates in place. **One session = one PR, ever.**
- Closing an auto PR is a permanent "don't share" signal — scanner won't re-open it.

To enable auto mode: `bash ~/.claude/skills/share-session/install.sh`. To disable: `bash ~/.claude/skills/share-session/uninstall.sh`. Full docs in the skill's `README.md`.

The manual `+share-session "<title>"` workflow still works the same as before — auto mode is purely additive.

## What this skill does NOT do

- Real-time mirroring (V2, planned)
- LLM-based summarization (V3, planned)
- Auto-push of every session (V1.5 auto mode is opt-in by project + multiple filters; not a blanket auto-share)
- Review gate / approval flow (PR itself is the review gate)
- Customer-facing redaction (team-internal V1 only)

See `README.md` next to this file for installation, configuration, and the auto-mode design notes.
