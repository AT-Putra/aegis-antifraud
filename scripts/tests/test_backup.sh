#!/usr/bin/env bash
# AC-BACKUP-01: seed penanda → backup → restore ke DB scratch → verifikasi konsisten → bersih.
# Host-level (butuh docker + stack jalan). Pakai: scripts/tests/test_backup.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

set -a; [ -f .env ] && . ./.env; set +a
PG_USER="${POSTGRES_USER:-aegis}"; PG_DB="${POSTGRES_DB:-aegis}"
CH_USER="${CLICKHOUSE_USER:-aegis}"; CH_PASS="${CLICKHOUSE_PASSWORD:-}"; CH_DB="${CLICKHOUSE_DB:-aegis}"
DC=(docker compose)
PSQL=( "${DC[@]}" exec -T postgres psql -v ON_ERROR_STOP=1 -U "$PG_USER" )
CHC=( "${DC[@]}" exec -T clickhouse clickhouse-client -u "$CH_USER" --password "$CH_PASS" )

if ! "${DC[@]}" ps postgres 2>/dev/null | grep -q .; then echo "SKIP: stack tak jalan"; exit 0; fi

SCRATCH="aegis_bktest"
KEY="bktest_$$_$(date +%s)"
TRX="bktest-$$-$(date +%s)"

cleanup() {
  "${PSQL[@]}" -d "$PG_DB" -c "DELETE FROM app_settings WHERE key='$KEY'" >/dev/null 2>&1 || true
  "${CHC[@]}" -d "$CH_DB" -q "DELETE FROM decision_log WHERE trx_id='$TRX'" >/dev/null 2>&1 || true
  "${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH" >/dev/null 2>&1 || true
  "${CHC[@]}" -q "DROP DATABASE IF EXISTS \`$SCRATCH\`" >/dev/null 2>&1 || true
  [ -n "${TS:-}" ] && rm -f "backups/pg_${TS}.sql.gz" "backups/ch_${TS}_"* 2>/dev/null || true
}
trap cleanup EXIT

echo "[test] seed penanda PG+CH"
"${PSQL[@]}" -d "$PG_DB" -c "INSERT INTO app_settings (key, value) VALUES ('$KEY','marker')" >/dev/null
"${CHC[@]}" -d "$CH_DB" -q "INSERT INTO decision_log (trx_id, decision) VALUES ('$TRX','allow')" < /dev/null

echo "[test] backup"
TS="$(BACKUP_DIR=backups RETENTION_DAYS=7 bash scripts/backup.sh | tail -n1)"
[ -f "backups/pg_${TS}.sql.gz" ] || { echo "FAIL: dump PG tak ada"; exit 1; }

echo "[test] restore → scratch '$SCRATCH'"
"${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH" >/dev/null
"${PSQL[@]}" -d postgres -c "CREATE DATABASE $SCRATCH" >/dev/null
bash scripts/restore.sh "$TS" "$SCRATCH" "$SCRATCH" >/dev/null

echo "[test] verifikasi konsistensi"
PG_N="$("${PSQL[@]}" -tA -d "$SCRATCH" -c "SELECT count(*) FROM app_settings WHERE key='$KEY'")"
CH_N="$("${CHC[@]}" -d "$SCRATCH" -q "SELECT count() FROM decision_log WHERE trx_id='$TRX'")"
echo "  PG marker=$PG_N  CH marker=$CH_N"
if [ "$PG_N" = "1" ] && [ "$CH_N" = "1" ]; then
  echo "PASS: backup→restore konsisten (PG+CH)"
else
  echo "FAIL: penanda tak konsisten setelah restore"; exit 1
fi
