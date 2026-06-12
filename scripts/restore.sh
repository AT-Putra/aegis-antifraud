#!/usr/bin/env bash
# T-19 — Restore MANUAL dari dump (non-goal: auto-restore).
# Pakai: scripts/restore.sh <TS> [PG_TARGET_DB] [CH_TARGET_DB]
#   default target = DB asli (.env). Untuk uji aman, beri DB scratch.
set -euo pipefail
cd "$(dirname "$0")/.."

TS="${1:?ts dump wajib (mis. 20260612-020000)}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
set -a; [ -f .env ] && . ./.env; set +a
PG_USER="${POSTGRES_USER:-aegis}"
CH_USER="${CLICKHOUSE_USER:-aegis}"; CH_PASS="${CLICKHOUSE_PASSWORD:-}"; CH_DB="${CLICKHOUSE_DB:-aegis}"
PG_TARGET="${2:-${POSTGRES_DB:-aegis}}"
CH_TARGET="${3:-$CH_DB}"
DC=(docker compose)
PSQL=( "${DC[@]}" exec -T postgres psql -v ON_ERROR_STOP=1 -U "$PG_USER" )
CHC=( "${DC[@]}" exec -T clickhouse clickhouse-client -u "$CH_USER" --password "$CH_PASS" )

echo "[restore] PostgreSQL → db '$PG_TARGET'"
gunzip -c "$BACKUP_DIR/pg_${TS}.sql.gz" | "${PSQL[@]}" -d "$PG_TARGET"

echo "[restore] ClickHouse skema → db '$CH_TARGET'"
"${CHC[@]}" -q "CREATE DATABASE IF NOT EXISTS \`$CH_TARGET\`"
# Ganti qualifier db sumber → target, lalu jalankan multi-statement.
sed "s/\b${CH_DB}\./${CH_TARGET}./g" "$BACKUP_DIR/ch_${TS}_schema.sql" \
  | "${CHC[@]}" -d "$CH_TARGET" --multiquery

echo "[restore] ClickHouse data (Native)"
for f in "$BACKUP_DIR"/ch_${TS}_*.native.gz; do
  t="$(basename "$f" .native.gz)"; t="${t#ch_${TS}_}"
  echo "  → $t"
  gunzip -c "$f" | "${CHC[@]}" -d "$CH_TARGET" -q "INSERT INTO \`$t\` FORMAT Native"
done

echo "[restore] selesai (pg=$PG_TARGET ch=$CH_TARGET ts=$TS)"
