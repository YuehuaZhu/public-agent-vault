# share-session

A Claude Code skill that lets you share your AI conversations with your team via GitHub. Two modes:

- **Manual** — say `+share-session "<title>"` to push the current session as a PR
- **Auto** (V1.5, opt-in) — a tiny macOS launchd job watches for sessions that have been idle long enough and quietly pushes them, one session = one PR

## What you get

For each session shared, a directory in the team repo contains:

```
projects/<your-github-user>/<project>/<dir>/
├── session.jsonl       (raw transcript, secrets redacted)
├── conversation.md     (rendered timeline, tool calls folded — same view in GitHub PR)
├── memory-snapshot/    (your Claude memory at share time)
└── meta.json
```

User messages are wrapped in a GitHub Alert (`[!IMPORTANT]`) so they pop out visually no matter how long the assistant response is.

## Install (macOS)

Prerequisites: `git`, [`gh` CLI](https://cli.github.com/) (logged in via `gh auth login`), `python3`, `envsubst` (`brew install gettext`).

```bash
# Clone (or copy) this skill into Claude Code's skills dir
git clone https://github.com/<owner>/claude-share-session ~/.claude/skills/share-session

# Or if you already have it as a normal skill, just run:
bash ~/.claude/skills/share-session/install.sh
```

The installer will:

1. Prompt for your **team repo URL** (e.g. `https://github.com/your-team/team-conversations.git`) and **GitHub username**
2. Ask which **projects** you want to auto-sync (basename of your project cwd, space-separated — leave blank to keep auto mode dormant)
3. Generate `~/Library/LaunchAgents/com.openwhispr.share-session.plist`
4. `launchctl load` it

After install, the scanner runs every 5 minutes. Logs are at `~/.claude/share-session/.logs/auto.log`.

## How auto mode decides what to push

A session gets auto-pushed only if **all** of these are true:

| Condition | Default | Where to change |
|---|---|---|
| Project listed in allowlist | `[]` (must add) | `auto-config.json::allowProjects` |
| JSONL idle for at least N minutes | `30` | `auto-config.json::idleMinutes` |
| At least N real user turns | `20` | `auto-config.json::minUserTurns` |
| Not in blocklist | `[]` | `auto-config.json::blockSessionIds` |
| User hasn't closed an earlier auto PR for this session | (state-tracked) | (auto) |

"Real user turns" excludes skill injections, system reminders, and tool results — only counts what you actually typed.

## How auto re-pushes work

Same session → same fixed branch `auto/<session-uuid>` → same PR, force-pushed on each refresh.

- First push: creates `auto/<uuid>` branch + PR
- You keep working in the same session → next idle period → force-push updates the same branch and PR
- You close the PR → scanner sees `CLOSED`, marks `userClosedPr: true`, never auto-touches this session again
- A different session (different UUID) → independent branch + PR

This means: **closing an auto PR is the unsubscribe button**. You stay in control.

## Manual mode

Still works exactly as before. From inside a Claude Code conversation:

> +share-session "客户需求 acme 第一次会"

Or from a terminal in your project directory:

```bash
bash ~/.claude/skills/share-session/share.sh --title "客户需求 acme 第一次会"
```

Manual mode uses a per-share unique branch (`shares/<date>-<slug>`) and always creates a fresh PR — it does not interfere with auto-mode PRs.

## Config files

```
~/.claude/share-session/
├── config.json              # team repo URL, your GitHub username (shared by both modes)
├── auto-config.json         # auto-mode rules
├── redaction-rules.json     # regex patterns for secret scrubbing
├── blocklist.txt            # custom words to redact (one per line)
├── auto-state.json          # per-session push state (auto-managed, don't edit)
├── repo/                    # local clone of team repo
├── pending/                 # failed manual pushes stashed here
└── .logs/                   # launchd log output
    ├── auto.log
    └── auto.err.log
```

## Privacy

Redacted automatically:
- API keys: OpenAI (`sk-...`), Anthropic (`sk-ant-...`), Google (`AIza...`), AWS access keys
- GitHub PATs (`ghp_...`, `github_pat_...`, `gho_...`)
- `Bearer <token>` headers
- Email addresses
- Anything in your `blocklist.txt`

**Not** redacted: customer / company / product names, file paths, business details. Auto mode is intended for **team-internal sharing only** (4–10 trusted people). If you need to share with external parties, use manual mode + heavy custom blocklist.

## Common operations

```bash
# See what auto mode would push, without actually pushing
python3 ~/.claude/skills/share-session/auto_scanner.py --dry-run

# Trigger a real scan immediately (don't wait for the 5-min tick)
python3 ~/.claude/skills/share-session/auto_scanner.py

# Check whether the launchd job is loaded
launchctl list | grep com.openwhispr.share-session

# Tail the log
tail -f ~/.claude/share-session/.logs/auto.log

# Block a specific session from ever being auto-pushed
# (edit auto-config.json: add the session UUID to blockSessionIds)

# Disable auto mode entirely
bash ~/.claude/skills/share-session/uninstall.sh

# Fully reset (delete all config and state)
bash ~/.claude/skills/share-session/uninstall.sh --purge
```

## Troubleshooting

**"share-session uses the wrong project name"** — auto mode reads each JSONL's `cwd` field to determine project. If you've moved a project or Claude Code mirrored a session across project dirs, the inferred project name might surprise you. Check `meta.json` in the pushed PR; if wrong, add the session UUID to `blockSessionIds`.

**"PR is empty / tiny content"** — Claude Code occasionally creates a near-empty placeholder JSONL with the same UUID in a different project dir (size ≈ 300 bytes). The auto mode filters this out via per-JSONL `cwd` matching, but if it slips through, the `minUserTurns ≥ 20` threshold should catch it.

**"Auto mode isn't pushing anything"** — Check `~/.claude/share-session/.logs/auto.log`. Most likely causes:
- `allowProjects` is empty in `auto-config.json`
- No session has crossed both the `idleMinutes` and `minUserTurns` thresholds yet
- `enabled: false` in `auto-config.json`

**"Pushed a session I didn't want shared"** — Close the PR on GitHub. Scanner sees CLOSED, sets `userClosedPr: true`, and never touches this session again. Optionally delete the branch too.

## V1.5 limitations (known)

- macOS only (Linux/Windows users: run scanner manually via cron until we add native support)
- No machine user — auto mode uses your personal `gh auth` token
- One conversation = one PR forever (no easy way to split mid-session)
- `~` is hard-coded in the launchd plist; if you move your home directory, re-run `install.sh`
