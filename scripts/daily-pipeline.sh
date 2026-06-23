#!/usr/bin/env bash
# GiinScore Daily Pipeline Runner
# ローカルのDocker Compose環境で定期的にパイプラインを実行する
#
# Usage:
#   ./scripts/daily-pipeline.sh              # 全パイプライン(session 221)
#   ./scripts/daily-pipeline.sh 221          # 会期番号を指定
#   ./scripts/daily-pipeline.sh 221 speeches # パイプラインを指定

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PROJECT_DIR}/logs"
SESSION="${1:-221}"
PIPELINE="${2:-all}"

mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/pipeline-$(date +%Y%m%d-%H%M%S).log"

cd "$PROJECT_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Pipeline started: session=${SESSION}, pipeline=${PIPELINE}" | tee "$LOG_FILE"

# Docker Composeが起動しているか確認
if ! docker compose ps --status running | grep -q backend; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Starting docker compose services..." | tee -a "$LOG_FILE"
  docker compose up -d db backend 2>&1 | tee -a "$LOG_FILE"
  sleep 10
fi

# パイプライン実行
docker compose exec -T backend python -m app.pipeline.runner \
  --pipeline "$PIPELINE" --session "$SESSION" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Pipeline completed successfully" | tee -a "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] Pipeline failed with exit code $EXIT_CODE" | tee -a "$LOG_FILE"
fi

# 古いログを削除（30日以上前）
find "$LOG_DIR" -name "pipeline-*.log" -mtime +30 -delete 2>/dev/null || true

echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Log saved to: $LOG_FILE"
exit $EXIT_CODE
