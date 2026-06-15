"""T-20: guard bootstrap admin & docs-off di produksi (gate go-live).

Guard berjalan SEBELUM akses DB, jadi bisa diuji unit tanpa Postgres.
"""

import pytest

from aegis import main
from aegis.config import Settings

_STRONG = "Zk7Q1pWm9rTxVb2NcHsLdFgYj4Ee8Au06oP"


def test_bootstrap_admin_rejects_weak_creds_in_production(monkeypatch) -> None:
    s = Settings(
        _env_file=None,
        app_env="production",
        admin_bootstrap_username="admin",
        admin_bootstrap_password="dev-change-me-strong-password",
    )
    monkeypatch.setattr(main, "get_settings", lambda: s)
    with pytest.raises(RuntimeError, match="ADMIN_BOOTSTRAP"):
        main._bootstrap_admin()


def test_bootstrap_admin_noop_when_unset(monkeypatch) -> None:
    # Tanpa username/password: tetap no-op (tidak raise) bahkan di produksi.
    # Bersihkan env proses (api container memuat .env dev) agar "unset" benar-benar kosong.
    monkeypatch.delenv("ADMIN_BOOTSTRAP_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_BOOTSTRAP_PASSWORD", raising=False)
    s = Settings(_env_file=None, app_env="production")
    monkeypatch.setattr(main, "get_settings", lambda: s)
    main._bootstrap_admin()  # tidak raise, tidak menyentuh DB
