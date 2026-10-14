"""Server-side image download with SSRF protection.

A moderation server that fetches arbitrary URLs can be abused to reach internal services
(cloud metadata endpoints, admin panels on localhost, ...). We therefore:

* only allow http(s),
* resolve the host ourselves and refuse private, loopback, link-local, reserved and
  multicast addresses (IPv4 and IPv6),
* follow redirects manually so every hop is re-validated,
* cap the download size and time.

DNS rebinding between our check and the connection remains theoretically possible; put the
server behind an egress proxy if URL fetching is exposed to untrusted callers.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

from openmoderate.io import MAX_BYTES

MAX_REDIRECTS = 3
TIMEOUT = 10


class UnsafeURLError(ValueError):
    pass


def _check_host(host: str, port: int) -> None:
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve host {host!r}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise UnsafeURLError(f"URL resolves to a non-public address ({ip})")


def validate_url(url: str) -> urllib.parse.SplitResult:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeURLError("Only http and https URLs are allowed")
    if not parts.hostname:
        raise UnsafeURLError("URL has no host")
    if parts.username or parts.password:
        raise UnsafeURLError("URLs with credentials are not allowed")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    _check_host(parts.hostname, port)
    return parts


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D102
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def fetch_image_bytes(url: str, max_bytes: int = MAX_BYTES) -> bytes:
    for _ in range(MAX_REDIRECTS + 1):
        validate_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": "openmoderate-server"})
        try:
            resp = _opener.open(req, timeout=TIMEOUT)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
                url = urllib.parse.urljoin(url, exc.headers["Location"])
                continue
            raise UnsafeURLError(f"Fetching URL failed with HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise UnsafeURLError(f"Fetching URL failed: {exc.reason}") from exc
        with resp:
            data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise UnsafeURLError(f"Image exceeds {max_bytes} bytes")
        return data
    raise UnsafeURLError("Too many redirects")
