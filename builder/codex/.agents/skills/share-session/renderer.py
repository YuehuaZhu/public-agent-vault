#!/usr/bin/env python3
"""Render a Claude Code JSONL transcript into Markdown for human reading.

Usage:
    python3 renderer.py --input <session.jsonl> --output <conversation.md> \
                        [--title "..."] [--sharer "@user"] [--project "name"]

Pure stdlib, no external deps. Deterministic — same input always produces same output.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

MAX_TOOL_RESULT_LINES = 50
HEAD_TAIL_LINES = 25  # when truncating, show first 25 + last 25

USER_ALERT_TYPE = "IMPORTANT"  # GFM alert flavor: NOTE/TIP/IMPORTANT/WARNING/CAUTION


def quote_block(text: str) -> str:
    """Prefix every line with '> ' for GFM blockquote/alert.

    GFM alerts terminate on a fully blank line, so empty lines become '>' to
    keep the alert container open across paragraph breaks.
    """
    lines = []
    for ln in text.split("\n"):
        lines.append(f"> {ln}" if ln else ">")
    return "\n".join(lines)


def load_lines(path: Path):
    events = []
    skipped = 0
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            skipped += 1
            events.append({"_malformed": True, "_line": i})
    return events, skipped


def fmt_ts(ts: str) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M:%S")
    except Exception:
        return ts


def fmt_date(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts or "?"


def duration_minutes(events) -> int:
    ts_list = [e.get("timestamp") for e in events if e.get("timestamp")]
    if len(ts_list) < 2:
        return 0
    try:
        first = datetime.fromisoformat(ts_list[0].replace("Z", "+00:00"))
        last = datetime.fromisoformat(ts_list[-1].replace("Z", "+00:00"))
        return int((last - first).total_seconds() / 60)
    except Exception:
        return 0


def truncate_text(s: str, max_lines: int = MAX_TOOL_RESULT_LINES) -> str:
    lines = s.split("\n")
    if len(lines) <= max_lines:
        return s
    head = lines[:HEAD_TAIL_LINES]
    tail = lines[-HEAD_TAIL_LINES:]
    omitted = len(lines) - HEAD_TAIL_LINES * 2
    return "\n".join(head + [f"\n[... {omitted} lines truncated ...]\n"] + tail)


def safe_fence(content: str) -> str:
    """Return a backtick fence longer than any backtick run inside content.

    CommonMark allows fences of any length >= 3; content can contain shorter runs.
    """
    longest = 0
    run = 0
    for ch in content:
        if ch == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return "`" * max(3, longest + 1)


def stringify_tool_result(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for block in content:
            if not isinstance(block, dict):
                out.append(str(block))
                continue
            btype = block.get("type")
            if btype == "text":
                out.append(block.get("text", ""))
            elif btype == "image":
                src = block.get("source", {})
                mt = src.get("media_type", "image")
                data = src.get("data", "")
                out.append(f"[image: {mt}, {len(data)} chars base64]")
            else:
                out.append(json.dumps(block, ensure_ascii=False))
        return "\n".join(out)
    return json.dumps(content, ensure_ascii=False)


def short_tool_summary(tool_use: dict) -> str:
    name = tool_use.get("name", "tool")
    inp = tool_use.get("input", {})
    if not isinstance(inp, dict):
        return name
    for key in ("file_path", "path", "command", "url", "query", "description", "skill", "pattern"):
        if key in inp:
            val = str(inp[key])
            return f"{name} · {val[:80]}"
    return name


def render_tool_use(tool_use: dict, results_by_id: dict) -> str:
    name = tool_use.get("name", "tool")
    tool_id = tool_use.get("id", "")
    summary = short_tool_summary(tool_use)
    inp = tool_use.get("input", {})
    result = results_by_id.get(tool_id)

    parts = [f"<details><summary>🔧 {summary}</summary>\n"]
    parts.append(f"**Tool**: `{name}`\n")
    inp_str = truncate_text(json.dumps(inp, ensure_ascii=False, indent=2))
    fence_in = safe_fence(inp_str)
    parts.append(f"**Input**:\n\n{fence_in}json\n{inp_str}\n{fence_in}\n")
    if result is not None:
        result_text = truncate_text(stringify_tool_result(result.get("content")))
        fence_out = safe_fence(result_text)
        parts.append(f"**Output**:\n\n{fence_out}\n{result_text}\n{fence_out}\n")
    else:
        parts.append("_(no tool result captured)_\n")
    parts.append("</details>\n")
    return "\n".join(parts)


def collect_tool_results(events):
    by_id = {}
    for ev in events:
        if ev.get("type") != "user":
            continue
        msg = ev.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                tid = block.get("tool_use_id")
                if tid:
                    by_id[tid] = block
    return by_id


def build_uuid_type_map(events):
    """Map event uuid → event type, so we can classify user events by parent."""
    m = {}
    for ev in events:
        u = ev.get("uuid")
        if u:
            m[u] = ev.get("type")
    return m


def is_real_user_input(ev, uuid_type_map) -> bool:
    """True iff this 'user' event is the human's typed/spoken input (not a
    skill injection, tool_result, or system reminder).

    Rule (derived from Claude Code transcript schema):
      - type == 'user'
      - has at least one non-empty text block
      - parentUuid is None (session-opener) OR parent's type == 'assistant'
        (skill injections have parent.type == 'user', as they follow a
        tool_result user-event).
      - text doesn't look like skill body or wrapped system-reminder.
    """
    if ev.get("type") != "user":
        return False
    msg = ev.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, list):
        return False
    text_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "text"]
    if not text_blocks:
        return False

    parent_uuid = ev.get("parentUuid")
    if parent_uuid is not None:
        parent_type = uuid_type_map.get(parent_uuid)
        if parent_type == "user":
            return False  # skill / system injection that follows a tool_result

    first_text = (text_blocks[0].get("text") or "").lstrip()
    if first_text.startswith("Base directory for this skill:"):
        return False
    if first_text.startswith("<system-reminder>") or first_text.startswith("<command-message"):
        return False

    return True


def get_title_from_events(events) -> str:
    for ev in events:
        if ev.get("type") == "ai-title" and ev.get("aiTitle"):
            return ev["aiTitle"]
    return ""


def get_session_id(events) -> str:
    for ev in events:
        if ev.get("sessionId"):
            return ev["sessionId"]
    return "?"


def get_first_timestamp(events) -> str:
    for ev in events:
        if ev.get("timestamp"):
            return ev["timestamp"]
    return ""


def count_turns(events) -> int:
    return sum(1 for e in events if e.get("type") == "user" and isinstance(e.get("message"), dict)
               and isinstance(e["message"].get("content"), list)
               and any(b.get("type") == "text" for b in e["message"]["content"] if isinstance(b, dict)))


def render(events, title: str, sharer: str, project: str, malformed: int) -> str:
    ai_title = get_title_from_events(events)
    display_title = title or ai_title or "Untitled Session"
    session_id = get_session_id(events)
    started = get_first_timestamp(events)
    duration = duration_minutes(events)
    turns = count_turns(events)

    out = []
    out.append(f"# {display_title}\n")
    out.append("")
    out.append(f"- **Sharer**: {sharer or '(unknown)'}")
    if project:
        out.append(f"- **Project**: {project}")
    out.append(f"- **Session**: `{session_id}`")
    out.append(f"- **Started**: {fmt_date(started)}")
    out.append(f"- **Duration**: {duration} min")
    out.append(f"- **User turns**: {turns}")
    if ai_title and ai_title != display_title:
        out.append(f"- **Auto-title**: {ai_title}")
    if malformed:
        out.append(f"- ⚠️ **Malformed lines skipped**: {malformed}")
    out.append("")
    out.append("---\n")

    results_by_id = collect_tool_results(events)
    uuid_type_map = build_uuid_type_map(events)
    injected_count = 0

    for ev in events:
        if ev.get("_malformed"):
            out.append(f"_[skipped malformed line {ev['_line']}]_\n")
            continue
        t = ev.get("type")
        if t not in ("user", "assistant"):
            continue
        msg = ev.get("message") or {}
        content = msg.get("content")
        ts = fmt_ts(ev.get("timestamp", ""))

        if t == "user":
            # String content (rare) → assume real user input
            if isinstance(content, str):
                if content.strip():
                    body = f"### 👤 User · {ts}\n\n{content.strip()}"
                    out.append(f"> [!{USER_ALERT_TYPE}]")
                    out.append(quote_block(body))
                    out.append("")
                continue
            if not isinstance(content, list):
                continue

            # Only render as User section if this is real human input.
            # Skill injections, system reminders, and bare tool_results are
            # filtered out — they were noise in V1.
            if not is_real_user_input(ev, uuid_type_map):
                # Detect skill/system injection text blocks so we can show a count
                has_text = any(isinstance(b, dict) and b.get("type") == "text" and (b.get("text") or "").strip()
                               for b in content)
                if has_text:
                    injected_count += 1
                continue

            user_texts = [b.get("text", "") for b in content
                          if isinstance(b, dict) and b.get("type") == "text"]
            user_texts = [tx for tx in user_texts if tx.strip()]
            if user_texts:
                joined = "\n\n".join(tx.strip() for tx in user_texts)
                body = f"### 👤 User · {ts}\n\n{joined}"
                out.append(f"> [!{USER_ALERT_TYPE}]")
                out.append(quote_block(body))
                out.append("")  # blank line ends the alert
        elif t == "assistant":
            if not isinstance(content, list):
                continue
            section_opened = False
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text = block.get("text", "").strip()
                    if not text:
                        continue
                    if not section_opened:
                        out.append(f"## 🤖 Assistant · {ts}\n")
                        section_opened = True
                    out.append(text + "\n")
                elif btype == "tool_use":
                    if not section_opened:
                        out.append(f"## 🤖 Assistant · {ts}\n")
                        section_opened = True
                    out.append(render_tool_use(block, results_by_id))
                elif btype == "thinking":
                    pass  # skip thinking blocks
        out.append("")

    if injected_count:
        out.append("---\n")
        out.append(f"_Note: {injected_count} skill/system-injection event(s) were filtered from this view. Raw `session.jsonl` contains them if needed._\n")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--title", default="")
    ap.add_argument("--sharer", default="")
    ap.add_argument("--project", default="")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"[renderer] input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    events, skipped = load_lines(args.input)
    md = render(events, args.title, args.sharer, args.project, skipped)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(f"[renderer] wrote {args.output} ({len(events)} events, {skipped} malformed)", file=sys.stderr)


if __name__ == "__main__":
    main()
