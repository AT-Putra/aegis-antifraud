"""AC-CP-01..03: mint web-opt-in (mock CP via httpx.MockTransport)."""

import httpx

from aegis.cp.client import mint_weboptin_url
from aegis.security.hmac_auth import sign_outbound

_SECRET = "service-secret"
_URL = "https://cp.example/request-weboptin"


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_mint_success_and_signature(monkeypatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        ts = request.headers["X-Aegis-Timestamp"]
        body = request.content.decode()
        seen["sig_ok"] = request.headers["X-Aegis-Signature"] == sign_outbound(_SECRET, ts, body)
        seen["has_request_id"] = bool(request.headers.get("X-Aegis-Request-Id"))
        return httpx.Response(
            200, json={"status": "ok", "web_opt_in_url": "https://telco.example/o?token=abc"}
        )

    res = mint_weboptin_url(
        _URL, _SECRET, trx_id="t1", service="funzone", client=_client(handler)
    )
    assert res.weboptin_status == "minted"
    assert res.redirect_url.endswith("token=abc")
    assert res.host == "telco.example"
    assert "token" not in (res.host or "")  # host tak bocorkan token
    assert seen["sig_ok"] is True
    assert seen["has_request_id"] is True


def test_retry_on_5xx_then_fail() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500)

    res = mint_weboptin_url(_URL, _SECRET, trx_id="t2", service="funzone", client=_client(handler))
    assert res.weboptin_status == "failed"
    assert calls["n"] == 2  # 1 awal + 1 retry


def test_timeout_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    res = mint_weboptin_url(_URL, _SECRET, trx_id="t3", service="funzone", client=_client(handler))
    assert res.weboptin_status == "failed"
    assert res.reason.startswith("network")


def test_cp_status_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "error", "reason": "token_request_failed"})

    res = mint_weboptin_url(_URL, _SECRET, trx_id="t4", service="funzone", client=_client(handler))
    assert res.weboptin_status == "failed"
    assert res.reason == "token_request_failed"


def test_reject_insecure_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"status": "ok", "web_opt_in_url": "http://telco.example/o?token=abc"}
        )

    res = mint_weboptin_url(_URL, _SECRET, trx_id="t5", service="funzone", client=_client(handler))
    assert res.weboptin_status == "failed"
    assert res.reason == "insecure_url"
