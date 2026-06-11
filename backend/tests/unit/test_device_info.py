"""AC-FEAT (device-info): parse UA best-effort."""

from aegis.features.device_info import parse_device_info

_ANDROID = (
    "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Mobile Safari/537.36"
)
_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def test_android_chrome_mobile() -> None:
    info = parse_device_info(_ANDROID, {"model": "SM-S921B"})
    assert info["os"] == "Android"
    assert info["device_type"] == "mobile"
    assert info["browser"] == "Chrome"
    assert info["model"] == "SM-S921B"


def test_iphone_safari() -> None:
    info = parse_device_info(_IPHONE)
    assert info["os"] == "iOS"
    assert info["device_type"] == "mobile"
    assert info["browser"] == "Safari"


def test_desktop_windows_chrome() -> None:
    info = parse_device_info(_DESKTOP)
    assert info["os"] == "Windows"
    assert info["device_type"] == "desktop"
    assert info["browser"] == "Chrome"
