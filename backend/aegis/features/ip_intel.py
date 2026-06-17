"""Enrichment IP server-side (TQ-07: GeoLite2 + IP2Proxy LITE + Tor list, ADR-009).

Degrade anggun: bila file DB belum tersedia di GEOIP_DIR, kembalikan nilai unknown
(tanpa error) — sistem tetap jalan, sinyal IP kosong sampai DB dipasang.
"""

from __future__ import annotations

import os
from functools import lru_cache

from aegis.config import get_settings

_UNKNOWN: dict = {
    "country": None,
    "asn": None,
    "isp": None,
    "connection_type": None,
    "proxy_type": None,
    "is_datacenter": False,
    "vpn_proxy_tor": False,
    "is_mobile_carrier": False,
    "ip_reputation": None,
}

_VPN_PROXY_TYPES = {"VPN", "TOR", "PUB", "WEB", "RES"}
_DC_USAGE = {"DCH", "SES", "CDN"}

# Operator seluler Indonesia (sinyal POSITIF pelanggan asli, ADR-009). IP2Proxy LITE
# sering tak menandai usage_type=MOB untuk IP seluler asli → turunkan dari ASN/ISP
# (MaxMind). ASN = definitif (global-unik); nama ISP = fallback (digate ke negara ID).
_ID_MOBILE_ASNS = {
    23693,  # Telkomsel (PT Telekomunikasi Selular)
    4761,   # Indosat
    4795,   # Indosat Mega Media (IM2)
    24203,  # XL Axiata
    45727,  # Hutchison 3 Indonesia (Tri)
    24378,  # Smartfren (Smart Telecom)
}
_ID_MOBILE_NAME_HINTS = (
    "telkomsel",
    "telekomunikasi selular",
    "indosat",
    "xl axiata",
    "excelcomindo",
    "hutchison",
    "smartfren",
    "smart telecom",
)


def _is_id_mobile_carrier(asn: int | None, isp: str | None, country: str | None) -> bool:
    """True bila IP milik operator seluler ID utama (Telkomsel/Indosat/XL/Tri/Smartfren)."""
    if asn in _ID_MOBILE_ASNS:
        return True
    if country == "ID" and isp:
        low = isp.lower()
        return any(h in low for h in _ID_MOBILE_NAME_HINTS)
    return False


@lru_cache
def _city_reader():
    try:
        import geoip2.database

        path = os.path.join(get_settings().geoip_dir, "GeoLite2-City.mmdb")
        return geoip2.database.Reader(path) if os.path.exists(path) else None
    except Exception:
        return None


@lru_cache
def _asn_reader():
    try:
        import geoip2.database

        path = os.path.join(get_settings().geoip_dir, "GeoLite2-ASN.mmdb")
        return geoip2.database.Reader(path) if os.path.exists(path) else None
    except Exception:
        return None


@lru_cache
def _proxy_db():
    try:
        import IP2Proxy

        path = os.path.join(get_settings().geoip_dir, "IP2PROXY-LITE-PX11.BIN")
        if not os.path.exists(path):
            return None
        db = IP2Proxy.IP2Proxy()
        db.open(path)
        return db
    except Exception:
        return None


def enrich_ip(ip: str | None) -> dict:
    result = dict(_UNKNOWN)
    if not ip:
        return result

    city = _city_reader()
    if city is not None:
        try:
            result["country"] = city.city(ip).country.iso_code
        except Exception:
            pass

    asn = _asn_reader()
    if asn is not None:
        try:
            rec = asn.asn(ip)
            result["asn"] = rec.autonomous_system_number
            result["isp"] = rec.autonomous_system_organization
        except Exception:
            pass

    proxy = _proxy_db()
    if proxy is not None:
        try:
            rec = proxy.get_all(ip)
            ptype = (rec.get("proxy_type") or "").upper()
            usage = (rec.get("usage_type") or "").upper()
            result["proxy_type"] = ptype or None
            result["connection_type"] = usage or None
            result["vpn_proxy_tor"] = ptype in _VPN_PROXY_TYPES
            result["is_datacenter"] = ptype == "DCH" or usage in _DC_USAGE
            result["is_mobile_carrier"] = usage == "MOB"
        except Exception:
            pass

    # Operator seluler ID (dari ASN/ISP MaxMind) → sinyal positif. Lengkapi bila
    # IP2Proxy LITE tak menandai (usage_type kosong/"-" untuk IP seluler asli).
    if _is_id_mobile_carrier(result["asn"], result["isp"], result["country"]):
        result["is_mobile_carrier"] = True
        if not result["connection_type"] or result["connection_type"] == "-":
            result["connection_type"] = "MOB"

    return result
