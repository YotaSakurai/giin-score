#!/usr/bin/env bash
# GiinScore Daily Pipeline Runner
# ローカルのDocker Compose環境で定期的にパイプラインを実行する
# speech_qualityはOllamaアクセスのためホスト側で直接実行
#
# Usage:
#   ./scripts/daily-pipeline.sh              # 全パイプライン(session 221)
#   ./scripts/daily-pipeline.sh 221          # 会期番号を指定
#   ./scripts/daily-pipeline.sh 221 speeches # パイプラインを指定

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="${PROJECT_DIR}/backend"
LOG_DIR="${PROJECT_DIR}/logs"
SESSION="${1:-221}"
PIPELINE="${2:-all}"

mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/pipeline-$(date +%Y%m%d-%H%M%S).log"

cd "$PROJECT_DIR"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log "[INFO] Pipeline started: session=${SESSION}, pipeline=${PIPELINE}"

# Docker Composeが起動しているか確認
if ! docker compose ps --status running | grep -q backend; then
  log "[INFO] Starting docker compose services..."
  docker compose up -d db backend 2>&1 | tee -a "$LOG_FILE"
  sleep 10
fi

# .envからDB接続情報を読み込み
set -a
source "${PROJECT_DIR}/.env"
set +a
HOST_DB_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5433/${POSTGRES_DB}"

if [ "$PIPELINE" = "speech_quality" ]; then
  # speech_qualityはOllamaアクセスのためホスト側で直接実行
  log "[INFO] Running speech_quality on host (Ollama access required)"
  cd "$BACKEND_DIR"
  DATABASE_URL="$HOST_DB_URL" OLLAMA_BASE_URL="http://127.0.0.1:11434" \
    python3 -m app.pipeline.runner --pipeline speech_quality --session "$SESSION" 2>&1 | tee -a "$LOG_FILE"
elif [ "$PIPELINE" = "all" ]; then
  # allの場合: まずDocker内でspeech_quality以外を実行し、その後ホストでspeech_quality
  log "[INFO] Running main pipelines in Docker..."
  docker compose exec -T backend python -m app.pipeline.runner \
    --pipeline all --session "$SESSION" 2>&1 | tee -a "$LOG_FILE"

  log "[INFO] Running speech_quality on host (Ollama access)..."
  cd "$BACKEND_DIR"
  DATABASE_URL="$HOST_DB_URL" OLLAMA_BASE_URL="http://127.0.0.1:11434" \
    python3 -m app.pipeline.runner --pipeline speech_quality --session "$SESSION" 2>&1 | tee -a "$LOG_FILE"

  # speech_quality後にスコア再計算
  log "[INFO] Re-scoring after speech_quality..."
  docker compose exec -T backend python -m app.pipeline.runner \
    --pipeline scoring --session "$SESSION" 2>&1 | tee -a "$LOG_FILE"
else
  # 個別パイプライン: Docker内で実行
  docker compose exec -T backend python -m app.pipeline.runner \
    --pipeline "$PIPELINE" --session "$SESSION" 2>&1 | tee -a "$LOG_FILE"
fi

EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
  log "[INFO] Pipeline completed successfully"
else
  log "[ERROR] Pipeline failed with exit code $EXIT_CODE"
fi

# 古いログを削除（30日以上前）
find "$LOG_DIR" -name "pipeline-*.log" -mtime +30 -delete 2>/dev/null || true

log "[INFO] Log saved to: $LOG_FILE"
exit $EXIT_CODE
