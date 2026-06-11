"""AC-INFRA-01 (sebagian): konfigurasi 12-factor termuat dengan default aman."""

from aegis.config import Settings


def test_settings_load_defaults() -> None:
    s = Settings(_env_file=None)
    assert s.app_env == "development"
    assert s.tz_default == "Asia/Jakarta"
    assert s.postgres_port == 5432


def test_postgres_dsn_composed() -> None:
    s = Settings(_env_file=None, postgres_user="u", postgres_password="p",
                 postgres_host="h", postgres_port=5432, postgres_db="d")
    assert s.postgres_dsn == "postgresql://u:p@h:5432/d"
