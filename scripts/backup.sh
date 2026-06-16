#!/usr/bin/env bash
# T-19 — Dump terjadwal minimal PostgreSQL + ClickHouse (auto-restore = non-goal, TRD §9).
# Pakai: scripts/backup.sh   |  cron: 0 2 * * * /path/scripts/backup.sh >> /var/log/aegis-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Kredensial dari .env (tak di-hardcode).
set -a; [ -f .env ] && . ./.env; set +a
PG_USER="${POSTGRES_USER:-aegis}"; PG_DB="${POSTGRES_DB:-aegis}"
CH_USER="${CLICKHOUSE_USER:-aegis}"; CH_PASS="${CLICKHOUSE_PASSWORD:-}"; CH_DB="${CLICKHOUSE_DB:-aegis}"
DC=(docker compose)
CH=( "${DC[@]}" exec -T clickhouse clickhouse-client -u "$CH_USER" --password "$CH_PASS" -d "$CH_DB" )

echo "[backup] PostgreSQL → pg_${TS}.sql.gz"
"${DC[@]}" exec -T postgres pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$BACKUP_DIR/pg_${TS}.sql.gz"

echo "[backup] ClickHouse skema → ch_${TS}_schema.sql"
TABLES=$("${CH[@]}" -q "SHOW TABLES")
: > "$BACKUP_DIR/ch_${TS}_schema.sql"
for t in $TABLES; do
  "${CH[@]}" -q "SHOW CREATE TABLE \`$t\` FORMAT TSVRaw" >> "$BACKUP_DIR/ch_${TS}_schema.sql"
  printf ';\n' >> "$BACKUP_DIR/ch_${TS}_schema.sql"
done

echo "[backup] ClickHouse data (Native) → ch_${TS}_<tabel>.native.gz"
for t in $TABLES; do
  # Lewati tabel kosong: dump Native 0-baris memicu NO_DATA_TO_INSERT (code 108) saat restore.
  # Skema tetap di-dump (SHOW CREATE) → tabel kosong tetap dibuat ulang saat restore.
  n="$("${CH[@]}" -q "SELECT count() FROM \`$t\`" | tr -d '[:space:]')"
  [ "${n:-0}" -gt 0 ] || { echo "[backup] skip $t (0 baris)"; continue; }
  "${CH[@]}" -q "SELECT * FROM \`$t\` FORMAT Native" | gzip > "$BACKUP_DIR/ch_${TS}_${t}.native.gz"
done

echo "[backup] prune dump > ${RETENTION_DAYS} hari"
find "$BACKUP_DIR" -type f \( -name 'pg_*.sql.gz' -o -name 'ch_*' \) -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true

echo "[backup] selesai ts=$TS dir=$BACKUP_DIR"
echo "$TS"
