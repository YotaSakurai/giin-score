#!/bin/bash
# git push 後に CI の結果を待って通知するスクリプト
# Claude Code の PostToolUse hook から stdin で JSON を受け取る

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# git push を含むコマンドでなければスキップ
if ! echo "$COMMAND" | grep -q 'git push'; then
    exit 0
fi

# push 直後は run がまだ作成されていない場合があるので少し待つ
sleep 5

MAX_WAIT=120
INTERVAL=5
elapsed=0

RUN_ID=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null)
if [ -z "$RUN_ID" ]; then
    echo '{"result": "CI run not found"}' >&2
    exit 0
fi

while [ $elapsed -lt $MAX_WAIT ]; do
    STATUS=$(gh run view "$RUN_ID" --json status,conclusion --jq '.status + ":" + (.conclusion // "")' 2>/dev/null)
    case "$STATUS" in
        completed:success)
            echo "CI PASSED (run $RUN_ID)" >&2
            exit 0
            ;;
        completed:failure)
            FAILURES=$(gh run view "$RUN_ID" --json jobs --jq '[.jobs[] | select(.conclusion=="failure") | .name] | join(", ")' 2>/dev/null)
            echo "CI FAILED (run $RUN_ID) - Failed jobs: $FAILURES" >&2
            exit 2
            ;;
        completed:*)
            echo "CI finished: $STATUS (run $RUN_ID)" >&2
            exit 0
            ;;
    esac
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

echo "CI still running after ${MAX_WAIT}s (run $RUN_ID)" >&2
exit 0
