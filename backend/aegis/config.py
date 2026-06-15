"""Konfigurasi 12-factor dari environment (TRD §7, ADR-003).

Semua rahasia & koneksi dibaca dari env (.env saat dev). Tidak ada nilai
rahasia yang di-hardcode di sini.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Pola "lemah" untuk secret/password (T-20 hardening, gate go-live).
# Substring case-insensitive yang menandakan nilai dev/placeholder.
_WEAK_SUBSTRINGS = ("change-me", "dev-", "admin", "password", "secret")
_MIN_SECRET_LEN = 32


def is_weak_secret(value: str) -> bool:
    """True bila nilai kosong, terlalu pendek, atau mengandung pola placeholder."""
    if not value or len(value) < _MIN_SECRET_LEN:
        return True
    low = value.lower()
    return any(sub in low for sub in _WEAK_SUBSTRINGS)


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

    # Bootstrap admin awal (T-15) — dibuat saat startup bila tabel users kosong
    admin_bootstrap_username: str = ""
    admin_bootstrap_password: str = ""

    # Lokal & origin
    tz_default: str = "Asia/Jakarta"
    allowed_origins: str = ""

    # Proxy tepercaya (T-20): hanya peer ini yang X-Forwarded-For-nya dipercaya.
    # Kosong = default jaringan privat/loopback (Caddy di jaringan docker `aegis`).
    # Daftar CIDR dipisah koma utk override (mis. "10.0.0.0/8,172.16.0.0/12").
    trusted_proxies: str = ""

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

    @property
    def is_production(self) -> bool:
        """Mode strict bila bukan development (T-20). Set APP_ENV=production di prod."""
        return self.app_env != "development"

    def validate_production(self) -> None:
        """Fail-fast: tolak boot bila secret/password masih kosong/default/lemah.

        Hanya berlaku saat ``is_production`` (APP_ENV != development). Mengumpulkan
        SEMUA pelanggaran lalu raise sekali agar ops melihat daftar lengkap.
        Gate go-live T-20 — cegah produksi jalan dengan key mudah ditebak.
        """
        if not self.is_production:
            return
        secrets = {
            "SESSION_SIGNING_KEY": self.session_signing_key,
            "JWT_SECRET": self.jwt_secret,
            "SECRET_ENC_KEY": self.secret_enc_key,
            "BILLING_HMAC_SECRET": self.billing_hmac_secret,
            "POSTGRES_PASSWORD": self.postgres_password,
            "CLICKHOUSE_PASSWORD": self.clickhouse_password,
        }
        weak = [name for name, val in secrets.items() if is_weak_secret(val)]
        if weak:
            raise RuntimeError(
                "APP_ENV="
                f"{self.app_env}: secret/password produksi lemah atau belum di-set: "
                f"{', '.join(weak)}. Wajib acak kuat (≥32 karakter, tanpa pola "
                "'change-me/dev-/admin/password/secret')."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
