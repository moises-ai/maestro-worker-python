from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

# Ports implied by their scheme carry no information, and keeping them would make
# ``https://host:443/x`` and ``https://host/x`` read as two different locations.
_DEFAULT_PORTS = {
    "ftp": 21,
    "http": 80,
    "https": 443,
    "ws": 80,
    "wss": 443,
}

# Substituted for a URL that cannot be parsed. An unparseable string is the one
# case where there is no way to show it holds no credential, so none of it is kept.
UNPARSEABLE_URL = "<unparseable-url>"


def sanitize_url(url: str) -> str:
    """Strip credentials and signing material from a URL while keeping it identifiable.

    Removes userinfo, query, and fragment, lowercases scheme and host, and drops
    the scheme's default port. The path is passed through byte-for-byte: decoding
    it would let percent-encoded data be reinterpreted as structure, and
    re-encoding it would change which object the URL names.

    The result is safe to log but is not anonymous — it still names an object.
    """
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return UNPARSEABLE_URL

    # hostname drops userinfo and lowercases in one step, unlike netloc.
    host = (parts.hostname or "").lower()

    if ":" in host:
        # An IPv6 literal loses the brackets it needs to round-trip.
        host = f"[{host}]"

    if port is not None and port != _DEFAULT_PORTS.get(parts.scheme.lower()):
        host = f"{host}:{port}"

    return urlunsplit((parts.scheme.lower(), host, parts.path, "", ""))
