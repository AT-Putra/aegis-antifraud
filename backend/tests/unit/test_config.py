"""AC-INFRA-01 (sebagian): konfigurasi 12-factor termuat dengan default aman."""

import pytest

from aegis.config import Settings, is_weak_secret

# Secret kuat contoh (≥32, tanpa pola placeholder) untuk skenario produksi valid.
_STRONG = "Zk7Q1pWm9rTxVb2NcHsLdFgYj4Ee8Au06oP"


def test_settings_load_defaults() -> None:
    s = Settings(_env_file=None)
    assert s.app_env == "development"
    assert s.tz_default == "Asia/Jakarta"
    assert s.postgres_port == 5432


def test_postgres_dsn_composed() -> None:
    s = Settings(_env_file=None, postgres_user="u", postgres_password="p",
                 postgres_host="h", postgres_port=5432, postgres_db="d")
    assert s.postgres_dsn == "postgresql://u:p@h:5432/d"


# --- T-20: fail-fast secret validation -------------------------------------

@pytest.mark.parametrize("value", [
    "",                                   # kosong
    "short",                              # < 32
    "dev-change-me-to-a-random-32-byte",  # mengandung 'change-me'/'dev-'
    "this-has-password-in-it-padded-xx",  # mengandung 'password'
    "supersecret-but-contains-secret-x",  # mengandung 'secret'
    "admin-admin-admin-admin-admin-adm",  # mengandung 'admin'
])
def test_is_weak_secret_rejects(value: str) -> None:
    assert is_weak_secret(value) is True


def test_is_weak_secret_accepts_strong() -> None:
    assert is_weak_secret(_STRONG) is False


def test_validate_production_noop_in_development() -> None:
    # Default development: tidak peduli secret lemah — tidak raise.
    Settings(_env_file=None, app_env="development").validate_production()


def test_validate_production_rejects_weak_secrets() -> None:
    s = Settings(_env_file=None, app_env="production")  # semua secret default ""
    with pytest.raises(RuntimeError) as exc:
        s.validate_production()
    msg = str(exc.value)
    # Daftar lengkap, bukan satu-satu.
    for name in ("SESSION_SIGNING_KEY", "JWT_SECRET", "SECRET_ENC_KEY",
                 "BILLING_HMAC_SECRET", "POSTGRES_PASSWORD", "CLICKHOUSE_PASSWORD"):
        assert name in msg


def test_validate_production_passes_with_strong_secrets() -> None:
    s = Settings(
        _env_file=None,
        app_env="production",
        session_signing_key=_STRONG,
        jwt_secret=_STRONG,
        secret_enc_key=_STRONG,
        billing_hmac_secret=_STRONG,
        postgres_password=_STRONG,
        clickhouse_password=_STRONG,
    )
    s.validate_production()  # tidak raise
