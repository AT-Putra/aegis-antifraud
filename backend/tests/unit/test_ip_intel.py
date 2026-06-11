"""AC-FEAT (enrichment): degrade anggun tanpa file DB (TQ-07)."""

from aegis.features.ip_intel import enrich_ip


def test_none_ip_returns_unknown() -> None:
    r = enrich_ip(None)
    assert r["country"] is None
    assert r["is_datacenter"] is False
    assert r["vpn_proxy_tor"] is False


def test_no_db_graceful_unknown() -> None:
    # File DB tidak ada di lingkungan test → harus unknown, TANPA error.
    r = enrich_ip("8.8.8.8")
    assert set(r.keys()) >= {
        "country", "asn", "is_datacenter", "vpn_proxy_tor", "is_mobile_carrier"
    }
    assert r["is_datacenter"] is False  # belum ada DB → default aman
