"""AC-FEAT (enrichment): degrade anggun tanpa file DB (TQ-07)."""

from aegis.features.ip_intel import _is_id_mobile_carrier, enrich_ip


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


# --- Deteksi operator seluler ID dari ASN/ISP (sinyal positif, ADR-009) ---


def test_carrier_telkomsel_by_asn() -> None:
    # Kasus nyata: ASN 23693 / "PT. Telekomunikasi Selular".
    assert _is_id_mobile_carrier(23693, "PT. Telekomunikasi Selular", "ID") is True


def test_carrier_known_asns_definitif_tanpa_negara() -> None:
    # ASN global-unik → ditandai walau country/isp tak tersedia.
    for asn in (4761, 4795, 24203, 45727, 24378):
        assert _is_id_mobile_carrier(asn, None, None) is True


def test_carrier_name_hint_di_negara_id() -> None:
    assert _is_id_mobile_carrier(999999, "Indosat Ooredoo Hutchison", "ID") is True
    assert _is_id_mobile_carrier(999999, "Smartfren Telecom", "ID") is True
    assert _is_id_mobile_carrier(999999, "XL Axiata", "ID") is True


def test_carrier_name_hint_butuh_negara_id() -> None:
    # Nama mengandung "hutchison" tapi negara bukan ID → JANGAN ditandai (cegah FP global).
    assert _is_id_mobile_carrier(999999, "Hutchison Global Comm", "SG") is False


def test_carrier_bukan_operator() -> None:
    assert _is_id_mobile_carrier(15169, "Google LLC", "US") is False
    assert _is_id_mobile_carrier(None, None, None) is False
    assert _is_id_mobile_carrier(999999, None, "ID") is False
