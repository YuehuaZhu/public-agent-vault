#!/usr/bin/env python3
"""Regex-based secret redactor for Claude Code transcripts.

Usage:
    python3 redactor.py --rules <rules.json> [--blocklist <blocklist.txt>] < in.jsonl > out.jsonl
    python3 redactor.py --rules <rules.json> --text "raw string"          # quick test

Reads JSONL (one JSON object per line) on stdin or scrubs a single string,
applies all regex rules + literal blocklist substrings, writes scrubbed lines.

Pure stdlib. No external deps.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def load_rules(rules_path: Path):
    data = json.loads(rules_path.read_text(encoding="utf-8"))
    compiled = []
    for r in data.get("rules", []):
        try:
            compiled.append((re.compile(r["pattern"]), r["replacement"], r.get("name", "?")))
        except re.error as e:
            print(f"[redactor] invalid pattern in rule '{r.get('name')}': {e}", file=sys.stderr)
    return compiled


def load_blocklist(blocklist_path: Path):
    if not blocklist_path or not blocklist_path.exists():
        return []
    words = []
    for line in blocklist_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            words.append(s)
    words.sort(key=len, reverse=True)
    return words


def redact_text(text: str, compiled_rules, blocklist) -> str:
    for pat, repl, _name in compiled_rules:
        text = pat.sub(repl, text)
    for word in blocklist:
        text = text.replace(word, "[REDACTED:custom]")
    return text


def redact_json_value(value, compiled_rules, blocklist):
    if isinstance(value, str):
        return redact_text(value, compiled_rules, blocklist)
    if isinstance(value, list):
        return [redact_json_value(v, compiled_rules, blocklist) for v in value]
    if isinstance(value, dict):
        return {k: redact_json_value(v, compiled_rules, blocklist) for k, v in value.items()}
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True, type=Path)
    ap.add_argument("--blocklist", type=Path, default=None)
    ap.add_argument("--text", type=str, default=None, help="Redact a single string and exit")
    args = ap.parse_args()

    compiled = load_rules(args.rules)
    blocklist = load_blocklist(args.blocklist) if args.blocklist else []

    if args.text is not None:
        sys.stdout.write(redact_text(args.text, compiled, blocklist))
        sys.stdout.write("\n")
        return

    for raw in sys.stdin:
        raw = raw.rstrip("\n")
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            sys.stdout.write(raw + "\n")
            continue
        scrubbed = redact_json_value(obj, compiled, blocklist)
        sys.stdout.write(json.dumps(scrubbed, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
