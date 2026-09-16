"""Local and VM network helpers. Internet is optional."""

from __future__ import annotations

import fcntl
import socket
import struct
from ipaddress import IPv4Address, IPv4Network, ip_address
from pathlib import Path

# QEMU user-net, VirtualBox NAT, and the Android emulator all map the host
# as 10.0.2.2 inside the guest. That address is not a NIC on this machine.
EMULATOR_GATEWAY = "10.0.2.2"
_DOCKER_LIBVIRT = IPv4Network("172.16.0.0/12")
_CGNAT = IPv4Network("100.64.0.0/10")  # Tailscale / CGNAT — treat like LAN


def guest_host_url(port: int, scheme: str = "http") -> str:
    """URL a nested VM or Android emulator should open (this host, no internet)."""
    return f"{scheme}://{EMULATOR_GATEWAY}:{int(port)}"


def address_kind(addr: str) -> str | None:
    """Classify an IPv4 string: lan, vm, public. None = skip."""
    try:
        ip = ip_address(addr)
    except ValueError:
        return None
    if not isinstance(ip, IPv4Address):
        return None
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return None
    if addr == EMULATOR_GATEWAY:
        return None
    if ip in _DOCKER_LIBVIRT:
        return "vm"
    if ip in _CGNAT:
        return "lan"
    if ip.is_global:
        return "public"
    if ip.is_private:
        return "lan"
    return None


def _usable(addr: str) -> bool:
    return address_kind(addr) is not None


def lan_ipv4_addresses() -> list[str]:
    """IPv4 addresses peers can use. LAN first, then public, then VM bridges."""
    found: list[str] = []
    seen: set[str] = set()

    def add(addr: str) -> None:
        if addr in seen:
            return
        if address_kind(addr) is None:
            return
        seen.add(addr)
        found.append(addr)

    for probe in ("192.168.255.255", "10.255.255.255", "172.16.255.255"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((probe, 1))
                add(sock.getsockname()[0])
        except OSError:
            pass

    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass

    try:
        for addr in socket.gethostbyname_ex(hostname)[2]:
            add(addr)
    except OSError:
        pass

    for addr in _linux_if_ipv4():
        add(addr)

    lan = [a for a in found if address_kind(a) == "lan"]
    public = [a for a in found if address_kind(a) == "public"]
    vm = [a for a in found if address_kind(a) == "vm"]
    return lan + public + vm


def public_base_urls(host: str, port: int, scheme: str = "http") -> list[str]:
    urls: list[str] = []
    if host in {"0.0.0.0", "::", ""}:
        for ip in lan_ipv4_addresses():
            urls.append(f"{scheme}://{ip}:{port}")
        urls.append(f"{scheme}://127.0.0.1:{port}")
    else:
        urls.append(f"{scheme}://{host}:{port}")
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            out.append(url)
            seen.add(url)
    return out


def connection_routes(
    host: str,
    port: int,
    online_url: str | None = None,
    scheme: str = "http",
) -> list[dict[str, str]]:
    """How a phone or second VM can reach this process. Internet is last and optional."""
    routes: list[dict[str, str]] = []
    if host in {"0.0.0.0", "::", ""}:
        for ip in lan_ipv4_addresses():
            kind = address_kind(ip) or "lan"
            if kind == "vm":
                label = "Two virtual machines (no internet)"
            elif kind == "public":
                label = "Public IP (often firewalled — try --online if this fails)"
            else:
                label = "Same Wi-Fi / LAN (no internet)"
            routes.append({"kind": kind, "label": label, "url": f"{scheme}://{ip}:{port}"})
    else:
        routes.append(
            {
                "kind": "lan",
                "label": "Bound address (no internet)",
                "url": f"{scheme}://{host}:{port}",
            }
        )

    routes.append(
        {
            "kind": "emulator",
            "label": "Android emulator / nested VM (no internet)",
            "url": guest_host_url(port, scheme),
            "note": "Inside the guest, 10.0.2.2 is this machine. QEMU, VirtualBox NAT, and the Android emulator all use it.",
        }
    )
    routes.append(
        {
            "kind": "usb",
            "label": "USB cable (no internet)",
            "url": f"{scheme}://127.0.0.1:{port}",
            "note": f"adb reverse tcp:{port} tcp:{port}",
        }
    )
    if online_url:
        routes.append(
            {
                "kind": "internet",
                "label": "Internet (phone on another network)",
                "url": online_url,
                "note": "Both devices need internet. Optional — skip this when the phone and laptop already share a LAN or VM network.",
            }
        )
    return routes


def format_connect_help(host: str, port: int, online_url: str | None = None, scheme: str = "http") -> str:
    """Human-readable connection block printed at startup."""
    lines = [
        "Connect — internet is NOT required:",
        "",
    ]
    routes = connection_routes(host, port, online_url, scheme=scheme)
    offline = [r for r in routes if r["kind"] != "internet"]
    online = [r for r in routes if r["kind"] == "internet"]
    for route in offline:
        lines.append(f"  {route['label']}")
        lines.append(f"    {route['url']}")
        if route.get("note"):
            lines.append(f"    {route['note']}")
        lines.append("")
    if online:
        lines.append("  Optional internet tunnel (only if the phone is on another network):")
        for route in online:
            lines.append(f"    {route['url']}")
        lines.append("")
    else:
        lines.append("  Phone on mobile data / another Wi-Fi? Rerun with --online.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _linux_if_ipv4() -> list[str]:
    """Best-effort NIC list so Docker/QEMU bridges show up on Linux VMs."""
    path = Path("/proc/net/dev")
    if not path.is_file():
        return []
    names: list[str] = []
    try:
        for line in path.read_text().splitlines()[2:]:
            if ":" not in line:
                continue
            name = line.split(":", 1)[0].strip()
            if name and name != "lo":
                names.append(name)
    except OSError:
        return []
    found: list[str] = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        return []
    try:
        for name in names:
            try:
                ifreq = struct.pack("256s", name[:15].encode("ascii", "ignore"))
                res = fcntl.ioctl(sock.fileno(), 0x8915, ifreq)  # SIOCGIFADDR
                found.append(socket.inet_ntoa(res[20:24]))
            except OSError:
                continue
    finally:
        sock.close()
    return found
