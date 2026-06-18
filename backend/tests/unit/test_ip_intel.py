"""AC-FEAT (enrichment): degrade anggun tanpa file DB (TQ-07)."""

from aegis.features.ip_intel import (
    _is_datacenter_provider,
    _is_id_mobile_carrier,
    enrich_ip,
)


def test_none_ip_returns_unknown() -> None:
    r = enrich_ip(None)
    assert r["country"] is None
    assert r["is_datacenter"] is False
    assert r["vpn_proxy_tor"] is False


def test_no_db_graceful_unknown(monkeypatch) -> None:
    # Tanpa file DB (reader None) → harus unknown, TANPA error. Reader dipaksa None agar
    # deterministik (mesin dgn GeoIP terpasang vs tidak).
    import aegis.features.ip_intel as mod

    monkeypatch.setattr(mod, "_city_reader", lambda: None)
    monkeypatch.setattr(mod, "_asn_reader", lambda: None)
    monkeypatch.setattr(mod, "_proxy_db", lambda: None)
    r = enrich_ip("8.8.8.8")
    assert set(r.keys()) >= {
        "country", "asn", "is_datacenter", "vpn_proxy_tor", "is_mobile_carrier"
    }
    assert r["is_datacenter"] is False  # tanpa DB → default aman


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


# --- Deteksi datacenter/hosting dari ASN/ISP (sinyal risiko, ADR-009) ---


def test_datacenter_hetzner_by_asn() -> None:
    # Kasus nyata produksi: 159.69.113.86 → ASN 24940 / "Hetzner Online GmbH".
    assert _is_datacenter_provider(24940, "Hetzner Online GmbH") is True


def test_datacenter_known_asns_definitif() -> None:
    # ASN hosting/cloud global-unik → ditandai walau nama ISP tak tersedia.
    for asn in (16276, 14061, 16509, 396982, 20473, 51167):
        assert _is_datacenter_provider(asn, None) is True


def test_datacenter_name_hint() -> None:
    assert _is_datacenter_provider(999999, "OVH SAS") is True
    assert _is_datacenter_provider(999999, "Amazon Data Services") is True
    assert _is_datacenter_provider(999999, "Some VPS Hosting Ltd") is True


def test_datacenter_bukan_hosting() -> None:
    # ISP residential/mobile → JANGAN ditandai datacenter.
    assert _is_datacenter_provider(23693, "PT Telekomunikasi Selular") is False
    assert _is_datacenter_provider(None, None) is False


def test_enrich_datacenter_via_ip2proxy_record(monkeypatch) -> None:
    # IP2Proxy LITE kosong (usage_type "-") tapi ASN Hetzner → is_datacenter dilengkapi.
    import aegis.features.ip_intel as mod

    class _Asn:
        def asn(self, ip):
            return type("R", (), {
                "autonomous_system_number": 24940,
                "autonomous_system_organization": "Hetzner Online GmbH",
            })()

    monkeypatch.setattr(mod, "_city_reader", lambda: None)
    monkeypatch.setattr(mod, "_asn_reader", lambda: _Asn())
    monkeypatch.setattr(mod, "_proxy_db", lambda: None)  # tak ada flag DCH dari LITE
    r = enrich_ip("159.69.113.86")
    assert r["asn"] == 24940
    assert r["is_datacenter"] is True
    assert r["connection_type"] == "DCH"
    assert r["is_mobile_carrier"] is False
