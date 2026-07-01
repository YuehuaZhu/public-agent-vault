#!/usr/bin/env python3
"""Periodic scanner for share-session auto-sync mode.

Invoked every N minutes by launchd. Reads ~/.claude/projects/*/*.jsonl,
applies the rules from auto-config.json, and triggers share.sh --auto on any
session that has been idle for >= idleMinutes and has >= minUserTurns real
user turns. State persisted in auto-state.json so re-pushes (force-push to
fixed branch) are detected and PRs are reused.

Pure stdlib + subprocess to share.sh. No external Python deps.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
STATE_DIR = Path.home() / ".claude" / "share-session"
PROJECTS_ROOT = Path.home() / ".claude" / "projects"
CONFIG_PATH = STATE_DIR / "auto-config.json"
STATE_PATH = STATE_DIR / "auto-state.json"
LOCK_PATH = STATE_DIR / "auto-scanner.lock"
SHARE_SH = SKILL_DIR / "share.sh"

sys.path.insert(0, str(SKILL_DIR))
from renderer import load_lines, build_uuid_type_map, is_real_user_input  # noqa: E402


def log(msg: str) -> None:
    print(f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[{dt.datetime.now().isoformat(timespec='seconds')}] ERROR {msg}",
          file=sys.stderr, flush=True)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        err(f"failed to read {path}: {e}")
        return default


def save_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _decode_project_name_fallback(encoded_dir: Path) -> str:
    """Heuristic fallback when no JSONL `cwd` field is available.

    `~/.claude/projects/-Users-alice-code-myproject/` → 'myproject'.
    Unreliable for project names containing '-' (e.g. 'my-cool-project').
    """
    name = encoded_dir.name
    parts = [p for p in name.lstrip("-").split("-") if p]
    return parts[-1] if parts else name


def project_name_for_jsonl(jsonl_path: Path) -> str | None:
    """Read the JSONL's own `cwd` field and return its basename.

    The encoded directory name `~/.claude/projects/-Users-x-MyCode-Foo/` is not
    a reliable project identifier — Claude Code sometimes mirrors a session
    across multiple project dirs. The authoritative source is the `cwd` field
    inside the events themselves.
    """
    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cwd = obj.get("cwd")
                if cwd:
                    return Path(cwd).name
    except Exception:
        pass
    return None


def iso(ts_epoch: float) -> str:
    return dt.datetime.fromtimestamp(ts_epoch, tz=dt.timezone.utc).isoformat(timespec="seconds")


def count_real_user_turns(jsonl_path: Path) -> int:
    """Use renderer's filter to count only true human inputs."""
    events, _skipped = load_lines(jsonl_path)
    uuid_type_map = build_uuid_type_map(events)
    return sum(1 for ev in events if is_real_user_input(ev, uuid_type_map))


def pr_state(pr_number: int) -> str | None:
    """Return 'OPEN' / 'CLOSED' / 'MERGED' or None on error."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number),
             "--repo", _config_repo_slug(),
             "--json", "state", "--jq", ".state"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        err(f"pr_state({pr_number}) failed: {e}")
    return None


_config_cache: dict = {}


def _config_repo_slug() -> str:
    """Derive 'owner/repo' from the configured repoUrl in config.json."""
    cfg = _config_cache.get("base") or load_json(STATE_DIR / "config.json", {})
    _config_cache["base"] = cfg
    url = cfg.get("repoUrl", "")
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?", url)
    return m.group(1) if m else ""


def run_share_sh_auto(session_id: str, project_name: str) -> tuple[bool, str]:
    """Call share.sh --auto. Returns (ok, pr_url_or_error)."""
    env = os.environ.copy()
    # share.sh resolves project from cwd by default; we override via --project
    cmd = ["bash", str(SHARE_SH), "--auto",
           "--session", session_id,
           "--project", project_name,
           "--title", f"auto-share {session_id[:8]}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env,
                                cwd=str(Path.home()))
    except Exception as e:
        return False, f"share.sh failed to launch: {e}"
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        return False, out
    return True, out


def parse_pr_number(share_sh_output: str) -> int | None:
    m = re.search(r"github\.com/[^/\s]+/[^/\s]+/pull/(\d+)", share_sh_output)
    return int(m.group(1)) if m else None


def acquire_lock():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return None
    return lock_file


def scan(dry_run: bool = False) -> int:
    config = load_json(CONFIG_PATH, {})
    if not config.get("enabled"):
        log("auto-sync disabled (or auto-config.json missing); exiting")
        return 0

    idle_seconds = int(config.get("idleMinutes", 30)) * 60
    min_user_turns = int(config.get("minUserTurns", 20))
    allow_projects = set(config.get("allowProjects", []))
    block_session_ids = set(config.get("blockSessionIds", []))

    if not PROJECTS_ROOT.exists():
        log(f"no projects dir at {PROJECTS_ROOT}")
        return 0

    state = load_json(STATE_PATH, {})
    now = time.time()
    actions = []

    for project_dir in sorted(PROJECTS_ROOT.iterdir()):
        if not project_dir.is_dir():
            continue

        for jsonl in sorted(project_dir.glob("*.jsonl")):
            session_id = jsonl.stem
            # Per-JSONL project resolution (encoded dir name is unreliable;
            # the `cwd` field inside the events is the authoritative source).
            project_name = project_name_for_jsonl(jsonl) \
                or _decode_project_name_fallback(project_dir)
            if "*" not in allow_projects and project_name not in allow_projects:
                continue
            entry = state.get(session_id, {})

            if entry.get("userClosedPr"):
                continue
            if session_id in block_session_ids:
                continue

            mtime_epoch = jsonl.stat().st_mtime
            mtime_iso = iso(mtime_epoch)

            if entry.get("lastPushedMtime") == mtime_iso:
                continue  # already pushed at this mtime

            if now - mtime_epoch < idle_seconds:
                # still active; just remember we saw it
                entry["lastSeenMtime"] = mtime_iso
                state[session_id] = entry
                continue

            user_turns = count_real_user_turns(jsonl)
            if user_turns < min_user_turns:
                continue

            existing_pr = entry.get("prNumber")
            if existing_pr:
                cur = pr_state(existing_pr)
                if cur == "CLOSED":
                    entry["userClosedPr"] = True
                    state[session_id] = entry
                    log(f"PR #{existing_pr} for {session_id[:8]} closed by user; skipping forever")
                    continue

            action_record = {
                "session_id": session_id,
                "project": project_name,
                "user_turns": user_turns,
                "mtime_iso": mtime_iso,
                "would_push_branch": f"auto/{session_id}",
                "existing_pr": existing_pr,
            }
            actions.append(action_record)

            if dry_run:
                log(f"[dry-run] would push session={session_id[:8]} project={project_name} "
                    f"turns={user_turns} existing_pr={existing_pr}")
                continue

            log(f"pushing session={session_id[:8]} project={project_name} turns={user_turns}")
            ok, output = run_share_sh_auto(session_id, project_name)
            if not ok:
                err(f"share.sh --auto failed for {session_id}: {output[-500:]}")
                entry["lastPushError"] = output[-500:]
                state[session_id] = entry
                continue

            pr_num = parse_pr_number(output) or existing_pr
            entry.update({
                "lastPushedMtime": mtime_iso,
                "lastSeenMtime": mtime_iso,
                "branch": f"auto/{session_id}",
                "prNumber": pr_num,
                "userTurns": user_turns,
                "userClosedPr": False,
                "lastPushError": None,
            })
            state[session_id] = entry
            log(f"pushed session={session_id[:8]} pr=#{pr_num}")

    save_state(state)
    log(f"scan done. {len(actions)} action(s).")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock()
    if lock is None:
        log("another scanner is running; exiting")
        return 0
    try:
        return scan(dry_run=args.dry_run)
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
