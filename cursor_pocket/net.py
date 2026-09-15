"""Local network helpers. No internet required."""

from __future__ import annotations

import socket
from ipaddress import ip_address


def lan_ipv4_addresses() -> list[str]:
    """Return likely LAN IPv4 addresses for this machine, best-first."""
    found: list[str] = []
    seen: set[str] = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.168.255.255", 1))
            primary = sock.getsockname()[0]
            if _usable(primary):
                found.append(primary)
                seen.add(primary)
    except OSError:
        pass

    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            addr = info[4][0]
            if addr not in seen and _usable(addr):
                found.append(addr)
                seen.add(addr)
    except OSError:
        pass

    try:
        for addr in socket.gethostbyname_ex(hostname)[2]:
            if addr not in seen and _usable(addr):
                found.append(addr)
                seen.add(addr)
    except OSError:
        pass

    return found


def public_base_urls(host: str, port: int) -> list[str]:
    urls: list[str] = []
    if host in {"0.0.0.0", "::", ""}:
        for ip in lan_ipv4_addresses():
            urls.append(f"http://{ip}:{port}")
        urls.append(f"http://127.0.0.1:{port}")
    else:
        urls.append(f"http://{host}:{port}")
    # de-dupe, keep order
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            out.append(url)
            seen.add(url)
    return out


def _usable(addr: str) -> bool:
    try:
        ip = ip_address(addr)
    except ValueError:
        return False
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False
    # Skip typical Docker/libvirt bridges unless that's all we have.
    if addr.startswith(("172.17.", "172.18.", "172.19.", "172.20.")):
        return False
    return ip.is_private or ip.is_global
