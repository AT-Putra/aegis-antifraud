"""Parse device-info best-effort dari UA + UA-CH (TRD §4.3). Untuk analitik & dimensi.

Tanpa dependency eksternal: heuristik ringan. Android model via UA-CH `model` (kode
mentah, mis. SM-S921B); pemetaan ke nama dagang = peningkatan masa depan. iOS generik.
"""

from __future__ import annotations

import re


def parse_device_info(user_agent: str | None, ua_data: dict | None = None) -> dict:
    ua = user_agent or ""
    info: dict = {
        "browser": None,
        "os": None,
        "device_type": "desktop",
        "brand": None,
        "model": None,
    }

    # OS
    if "Android" in ua:
        info["os"] = "Android"
    elif re.search(r"iPhone|iPad|iOS", ua):
        info["os"] = "iOS"
    elif "Windows" in ua:
        info["os"] = "Windows"
    elif "Mac OS" in ua:
        info["os"] = "macOS"
    elif "Linux" in ua:
        info["os"] = "Linux"

    # device type
    if "iPad" in ua or ("Android" in ua and "Mobile" not in ua):
        info["device_type"] = "tablet"
    elif re.search(r"Mobile|iPhone|Android", ua):
        info["device_type"] = "mobile"

    # browser (urutan penting: Edge/Samsung sebelum Chrome; Chrome sebelum Safari)
    if "Edg" in ua:
        info["browser"] = "Edge"
    elif "SamsungBrowser" in ua:
        info["browser"] = "Samsung Internet"
    elif "Chrome" in ua or "CriOS" in ua:
        info["browser"] = "Chrome"
    elif "Firefox" in ua or "FxiOS" in ua:
        info["browser"] = "Firefox"
    elif "Safari" in ua:
        info["browser"] = "Safari"

    # UA-CH (lebih andal bila tersedia)
    if ua_data:
        info["model"] = ua_data.get("model") or info["model"]
        if not info["os"] and ua_data.get("platform"):
            info["os"] = ua_data.get("platform")

    return info
