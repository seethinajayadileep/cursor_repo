"""Open a public HTTPS URL to this laptop so a phone on another network can connect."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

CLOUDFLARE_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)
NGROK_URL = re.compile(r"https://[a-z0-9.-]+\.ngrok(?:-free)?\.(?:app|io)", re.I)
GENERIC_HTTPS = re.compile(r"https://[a-z0-9.-]+\.[a-z]{2,}[a-z0-9./_-]*", re.I)


def parse_public_url(text: str) -> str | None:
    """Pick a tunnel URL out of cloudflared / ngrok log noise."""
    for pattern in (CLOUDFLARE_URL, NGROK_URL):
        match = pattern.search(text)
        if match:
            return match.group(0).rstrip("/")
    return None


@dataclass
class Tunnel:
    url: str
    proc: subprocess.Popen[str]
    kind: str
    _reader: threading.Thread | None = field(default=None, repr=False)

    def stop(self) -> None:
        if self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def start_tunnel(local_port: int, timeout: float = 30.0) -> Tunnel:
    """Expose http://127.0.0.1:port on the public internet. Needs cloudflared or ngrok."""
    target = f"http://127.0.0.1:{local_port}"
    cloudflared = _find_cloudflared()
    ngrok = shutil.which("ngrok")
    if cloudflared:
        return _spawn(
            [cloudflared, "tunnel", "--no-autoupdate", "--url", target],
            kind="cloudflared",
            timeout=timeout,
        )
    if ngrok:
        return _spawn(
            [ngrok, "http", str(local_port), "--log", "stdout", "--log-format", "term"],
            kind="ngrok",
            timeout=timeout,
        )
    raise SystemExit(_install_help())


def _spawn(cmd: list[str], *, kind: str, timeout: float) -> Tunnel:
    proc = subprocess.Popen(  # noqa: S603 — user-local tunnel binary
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    found: list[str] = []
    buffer: list[str] = []

    def read() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            buffer.append(line)
            url = parse_public_url(line)
            if url and not found:
                found.append(url)

    reader = threading.Thread(target=read, daemon=True, name=f"{kind}-log")
    reader.start()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if found:
            return Tunnel(url=found[0], proc=proc, kind=kind, _reader=reader)
        if proc.poll() is not None:
            break
        time.sleep(0.15)
    snippet = "".join(buffer[-20:]).strip() or f"{kind} exited without a public URL"
    proc.kill()
    raise SystemExit(f"Could not start the online tunnel ({kind}).\n{snippet}\n")


def _find_cloudflared() -> str | None:
    which = shutil.which("cloudflared")
    if which:
        return which
    local = Path.home() / ".cursor-pocket" / ("cloudflared.exe" if os.name == "nt" else "cloudflared")
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    return None


def _install_help() -> str:
    return """\
--online needs a tunnel binary so the phone can reach this laptop over the internet.

Option A — Cloudflare quick tunnel (HTTPS URL, no account):
  https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
  Then rerun with --online.

Option B — ngrok:
  https://ngrok.com/download
  ngrok config add-authtoken <token>
  Then rerun with --online.

Option C — Tailscale on phone and laptop (more private, no public URL):
  Install Tailscale on both devices, then open http://<laptop-tailscale-ip>:8787
  on the phone. Do not pass --online.
"""
