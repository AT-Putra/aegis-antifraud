"""T-20: client_ip hanya percaya X-Forwarded-For dari peer tepercaya (anti-spoof).

Cegah bypass rate-limit/login-throttle per-IP via header XFF yang dipalsukan klien.
"""

from starlette.requests import Request

from aegis.api.deps import client_ip


def _req(peer: str | None, xff: str | None = None) -> Request:
    headers = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    scope = {
        "type": "http",
        "headers": headers,
        "client": (peer, 12345) if peer else None,
    }
    return Request(scope)


def test_trusted_peer_honors_xff() -> None:
    # Peer = Caddy di jaringan privat → XFF dipercaya.
    assert client_ip(_req("172.18.0.5", "203.0.113.9")) == "203.0.113.9"


def test_trusted_peer_takes_first_xff_hop() -> None:
    assert client_ip(_req("10.0.0.2", "203.0.113.9, 10.0.0.2")) == "203.0.113.9"


def test_untrusted_peer_ignores_spoofed_xff() -> None:
    # Peer publik (akses langsung) → XFF diabaikan, pakai peer nyata.
    assert client_ip(_req("203.0.113.50", "1.2.3.4")) == "203.0.113.50"


def test_no_xff_uses_peer() -> None:
    assert client_ip(_req("172.18.0.5")) == "172.18.0.5"


def test_no_client_returns_none() -> None:
    assert client_ip(_req(None)) is None
