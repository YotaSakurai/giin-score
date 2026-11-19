#!/usr/bin/env bash
# 開発DB（ローカルパイプラインが更新）→ 本番/ステージングDB へデータを同期する。
#
# 使い方:
#   ローカル検証環境へ:  ./scripts/sync-db.sh local
#   VPS本番へ:          ./scripts/sync-db.sh vps user@your-vps-host
#
# 前提: 開発スタック(docker compose)の db が起動していること
set -euo pipefail

cd "$(dirname "$0")/.."
source .env  # POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB

TARGET="${1:-local}"
DUMP_FILE=$(mktemp /tmp/giinscore-dump-XXXXXX.sql.gz)
trap 'rm -f "$DUMP_FILE"' EXIT

echo "=== 開発DBからダンプ作成 ==="
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --no-owner --no-privileges | gzip > "$DUMP_FILE"
echo "ダンプサイズ: $(du -h "$DUMP_FILE" | cut -f1)"

restore_via_docker() {
  # $1: docker compose プロジェクト名
  local project="$1"
  echo "=== $project の db へリストア ==="
  docker compose -p "$project" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB}_restore;" >/dev/null
  # 一旦別名DBにリストアしてから入れ替え（ダウンタイム最小化）
  docker compose -p "$project" exec -T db \
    createdb -U "$POSTGRES_USER" "${POSTGRES_DB}_restore"
  gunzip -c "$DUMP_FILE" | docker compose -p "$project" exec -T db \
    psql -q -U "$POSTGRES_USER" -d "${POSTGRES_DB}_restore" >/dev/null
  docker compose -p "$project" exec -T db psql -U "$POSTGRES_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${POSTGRES_DB}_old;
ALTER DATABASE ${POSTGRES_DB} RENAME TO ${POSTGRES_DB}_old;
ALTER DATABASE ${POSTGRES_DB}_restore RENAME TO ${POSTGRES_DB};
DROP DATABASE ${POSTGRES_DB}_old;
SQL
  echo "リストア完了"
}

case "$TARGET" in
  local)
    restore_via_docker giin-score-prod
    ;;
  vps)
    VPS_HOST="${2:?vps ターゲットには user@host を指定してください}"
    echo "=== $VPS_HOST へ転送してリストア ==="
    scp "$DUMP_FILE" "$VPS_HOST:/tmp/giinscore-dump.sql.gz"
    ssh "$VPS_HOST" bash -s <<REMOTE
set -euo pipefail
cd ~/giin-score
source .env.production
gunzip -c /tmp/giinscore-dump.sql.gz > /tmp/giinscore-dump.sql
docker compose -p giin-score-prod exec -T db createdb -U "\$POSTGRES_USER" "\${POSTGRES_DB}_restore" || {
  docker compose -p giin-score-prod exec -T db dropdb -U "\$POSTGRES_USER" "\${POSTGRES_DB}_restore"
  docker compose -p giin-score-prod exec -T db createdb -U "\$POSTGRES_USER" "\${POSTGRES_DB}_restore"
}
docker compose -p giin-score-prod exec -T db psql -q -U "\$POSTGRES_USER" -d "\${POSTGRES_DB}_restore" < /tmp/giinscore-dump.sql >/dev/null
docker compose -p giin-score-prod exec -T db psql -U "\$POSTGRES_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE datname = '\${POSTGRES_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS \${POSTGRES_DB}_old;
ALTER DATABASE \${POSTGRES_DB} RENAME TO \${POSTGRES_DB}_old;
ALTER DATABASE \${POSTGRES_DB}_restore RENAME TO \${POSTGRES_DB};
DROP DATABASE \${POSTGRES_DB}_old;
SQL
rm -f /tmp/giinscore-dump.sql /tmp/giinscore-dump.sql.gz
echo "リストア完了"
REMOTE
    ;;
  *)
    echo "不明なターゲット: $TARGET (local | vps)" >&2
    exit 1
    ;;
esac
