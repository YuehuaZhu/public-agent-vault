#!/bin/bash
# Warn when current session approaches the slow-context zone.
# Threshold = warn-at line count. Edit to taste.
THRESHOLD=800

INPUT=$(cat)
SID=$(echo "$INPUT" | jq -r '.session_id // empty')
[ -z "$SID" ] && exit 0

F=$(find ~/.claude/projects -name "${SID}.jsonl" 2>/dev/null | head -1)
[ -z "$F" ] && exit 0

N=$(wc -l < "$F" | tr -d ' ')

if [ "$N" -ge "$THRESHOLD" ]; then
  printf '{"systemMessage":"⚠️  当前会话已 %s 行（阈值 %s）— 上下文较长会变慢，建议执行 /compact 压缩历史"}\n' "$N" "$THRESHOLD"
fi
