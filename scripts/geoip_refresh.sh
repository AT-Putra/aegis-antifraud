#!/usr/bin/env bash
# Refresh DB GeoIP (GeoLite2 City/ASN + IP2Proxy LITE PX11) lalu reload reader (restart api).
# Reader ip_intel pakai lru_cache → file baru hanya terbaca setelah `api` di-restart.
# Unduh ke temp + validasi dulu → ganti file live secara atomic (gagal unduh tak merusak yang lama).
#
# Pakai:  scripts/geoip_refresh.sh
# Cron bulanan (root, jam sepi):
#   0 3 1 * * root cd /opt/aegis-antifraud && /usr/bin/bash scripts/geoip_refresh.sh >> /var/log/aegis-geoip.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; [ -f .env ] && . ./.env; set +a
DEST="${GEOIP_HOST_DIR:-data/geoip}"            # lokasi file di HOST (mount → container GEOIP_DIR)
: "${MAXMIND_LICENSE_KEY:?set MAXMIND_LICENSE_KEY di .env}"
: "${IP2LOCATION_TOKEN:?set IP2LOCATION_TOKEN di .env}"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
MM="https://download.maxmind.com/app/geoip_download"

echo "[geoip] unduh GeoLite2 City + ASN"
curl -fsSL "${MM}?edition_id=GeoLite2-City&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz" -o "$TMP/city.tgz"
curl -fsSL "${MM}?edition_id=GeoLite2-ASN&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz"  -o "$TMP/asn.tgz"
tar -xzf "$TMP/city.tgz" --wildcards --strip-components=1 -C "$TMP" '*/GeoLite2-City.mmdb'
tar -xzf "$TMP/asn.tgz"  --wildcards --strip-components=1 -C "$TMP" '*/GeoLite2-ASN.mmdb'

echo "[geoip] unduh IP2Proxy LITE PX11"
curl -fsSL "https://www.ip2location.com/download/?token=${IP2LOCATION_TOKEN}&file=PX11LITEBIN" -o "$TMP/px11.zip"
unzip -o "$TMP/px11.zip" -d "$TMP" >/dev/null

echo "[geoip] validasi hasil unduh"
for f in GeoLite2-City.mmdb GeoLite2-ASN.mmdb IP2PROXY-LITE-PX11.BIN; do
  [ -s "$TMP/$f" ] || { echo "[geoip] GAGAL: $f tak terunduh/kosong"; exit 1; }
done
# MaxMind/IP2Location kadang membalas pesan error sebagai file kecil → tolak bila terlalu kecil.
[ "$(stat -c%s "$TMP/GeoLite2-City.mmdb")"     -gt 1000000 ] || { echo "[geoip] GAGAL: City mmdb terlalu kecil (cek MAXMIND_LICENSE_KEY)"; exit 1; }
[ "$(stat -c%s "$TMP/IP2PROXY-LITE-PX11.BIN")" -gt 1000000 ] || { echo "[geoip] GAGAL: PX11 BIN terlalu kecil (cek IP2LOCATION_TOKEN)"; exit 1; }

echo "[geoip] pasang file baru (atomic) → $DEST"
mkdir -p "$DEST"
for f in GeoLite2-City.mmdb GeoLite2-ASN.mmdb IP2PROXY-LITE-PX11.BIN; do
  mv -f "$TMP/$f" "$DEST/$f"
done

echo "[geoip] reload reader → restart api"
docker compose restart api

echo "[geoip] selesai $(date -u +%FT%TZ)"
