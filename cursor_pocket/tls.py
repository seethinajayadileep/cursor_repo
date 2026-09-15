"""Optional self-signed HTTPS so Android Chrome can install the PWA and notify."""

from __future__ import annotations

import shutil
import ssl
import subprocess
from http.server import HTTPServer
from pathlib import Path

from .net import lan_ipv4_addresses


def wrap_https(httpd: HTTPServer, cert_dir: Path | None = None) -> Path:
    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit(
            "HTTPS needs the openssl CLI on PATH, or omit --https and use plain HTTP on Wi-Fi."
        )
    folder = cert_dir or (Path.home() / ".cursor-pocket")
    folder.mkdir(parents=True, exist_ok=True)
    cert = folder / "cert.pem"
    key = folder / "key.pem"
    if not (cert.is_file() and key.is_file()):
        _generate(openssl, cert, key)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(cert), str(key))
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    return cert


def _generate(openssl: str, cert: Path, key: Path) -> None:
    sans = ["DNS:localhost", "IP:127.0.0.1"]
    for ip in lan_ipv4_addresses():
        sans.append(f"IP:{ip}")
    san = ",".join(sans)
    subprocess.run(  # noqa: S603 — local openssl, fixed args
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-sha256",
            "-days",
            "825",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            "/CN=Cursor Pocket",
            "-addext",
            f"subjectAltName={san}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
