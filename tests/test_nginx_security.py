from pathlib import Path
import re


NGINX_CONFIG = (
    Path(__file__).resolve().parents[1] / "rcongui" / "nginx.conf"
).read_text(encoding="utf-8")

SECURITY_HEADERS = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "X-Frame-Options",
    "Content-Security-Policy",
)


def _locations_with_local_headers():
    """Return locations that opt out of inherited server-level add_header."""
    return re.findall(
        r"^\s*location\s+.+?\s*\{(?P<body>.*?)^\s*\}",
        NGINX_CONFIG,
        flags=re.MULTILINE | re.DOTALL,
    )


def test_nginx_disables_legacy_tls_and_keeps_modern_protocols():
    protocols = re.findall(r"ssl_protocols\s+([^;]+);", NGINX_CONFIG)

    assert protocols == ["TLSv1.2 TLSv1.3", "TLSv1.2 TLSv1.3"]
    assert "TLSv1.1" not in NGINX_CONFIG
    assert "TLSv1;" not in NGINX_CONFIG


def test_nginx_security_headers_are_defined_with_https_only_hsts():
    assert 'map $https $hsts_header' in NGINX_CONFIG
    assert 'default "max-age=31536000";' in NGINX_CONFIG
    assert '""      "";' in NGINX_CONFIG

    for header in SECURITY_HEADERS:
        assert f"add_header {header}" in NGINX_CONFIG


def test_locations_with_cache_headers_keep_the_security_baseline():
    locations_with_local_headers = [
        location
        for location in _locations_with_local_headers()
        if "add_header" in location
    ]

    assert locations_with_local_headers
    for location in locations_with_local_headers:
        for header in SECURITY_HEADERS:
            assert f"add_header {header}" in location
