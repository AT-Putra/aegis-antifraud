"""Konfigurasi 12-factor dari environment (TRD §7, ADR-003).

Semua rahasia & koneksi dibaca dari env (.env saat dev). Tidak ada nilai
rahasia yang di-hardcode di sini.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # PostgreSQL (OLTP)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "aegis"
    postgres_password: str = ""
    postgres_db: str = "aegis"

    # ClickHouse (OLAP)
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "aegis"
    clickhouse_password: str = ""
    clickhouse_db: str = "aegis"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    # Keamanan (TRD §7) — wajib di-set via env di produksi
    session_signing_key: str = ""
    jwt_secret: str = ""
    secret_enc_key: str = ""  # master key AES-256-GCM untuk services.hmac_secret (TQ-08)
    billing_hmac_secret: str = ""  # shared secret callback billing (HMAC inbound)

    # Lokal & origin
    tz_default: str = "Asia/Jakarta"
    allowed_origins: str = ""

    # Model store (shared, ADR-003)
    model_dir: str = "/models"

    # IP intelligence (TQ-07: GeoLite2 + IP2Proxy LITE)
    geoip_dir: str = "/data/geoip"
    maxmind_account_id: str = ""
    maxmind_license_key: str = ""
    ip2location_token: str = ""

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
