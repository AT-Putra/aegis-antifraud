"""AC-SEC-01: session token single-use, terikat trx_id (butuh Redis)."""

import pytest

from aegis.db.redis import get_redis
from aegis.security.tokens import SessionTokenError, issue, verify_and_consume


def _redis_ok() -> bool:
    try:
        get_redis().ping()
        return True
    except Exception:
        return False


def test_token_single_use() -> None:
    if not _redis_ok():
        pytest.skip("Redis tak terjangkau")
    token, _ = issue("trx-001")
    verify_and_consume(token, "trx-001")  # pakai pertama: OK
    with pytest.raises(SessionTokenError):
        verify_and_consume(token, "trx-001")  # pakai kedua: ditolak


def test_token_trx_mismatch() -> None:
    if not _redis_ok():
        pytest.skip("Redis tak terjangkau")
    token, _ = issue("trx-aaa")
    with pytest.raises(SessionTokenError):
        verify_and_consume(token, "trx-bbb")


def test_token_bad_signature() -> None:
    if not _redis_ok():
        pytest.skip("Redis tak terjangkau")
    token, _ = issue("trx-002")
    payload_b64, _sig = token.split(".", 1)
    with pytest.raises(SessionTokenError):
        verify_and_consume(f"{payload_b64}.deadbeef", "trx-002")
