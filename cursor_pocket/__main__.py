"""python3 -m cursor_pocket — start the laptop daemon."""

from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

from . import __app_name__, __version__
from .auth import Auth
from .jobs import JobStore
from .net import public_base_urls
from .runner import Runner, find_agent
from .server import PocketHTTPServer, PocketState
from .tls import wrap_https


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    args = _parse(argv)
    workspaces = _workspaces(args.workspace)
    agent = None if args.demo else find_agent()
    if not args.demo and not agent:
        print(
            "No Cursor CLI (`agent`) found on PATH.\n"
            "Install it from https://cursor.com/docs/cli/overview\n"
            "or pass --demo to try the phone UI without running Cursor.\n",
            file=sys.stderr,
        )
        return 2

    auth = Auth.generate(args.pin)
    runner = Runner(demo=args.demo, force=not args.no_force, trust=not args.no_trust, agent_bin=agent)
    state = PocketState(
        auth=auth,
        store=JobStore(),
        runner=runner,
        workspaces=workspaces,
        host=args.host,
        port=args.port,
        laptop_name=args.name or socket.gethostname(),
    )
    httpd = PocketHTTPServer((args.host, args.port), state)
    scheme = "http"
    if args.https:
        wrap_https(httpd)
        scheme = "https"
    state.port = httpd.server_address[1]
    urls = public_base_urls(args.host, state.port)
    phone_urls = [u.replace("http://", f"{scheme}://", 1) for u in urls]
    host_url = f"{scheme}://127.0.0.1:{state.port}/host"

    print()
    print(f"{__app_name__} v{__version__}")
    print("Phone remote for Cursor CLI. Traffic stays on this machine's LAN.")
    print("Keep this window open while you use the phone.")
    print()
    print(f"  Laptop pairing page: {host_url}")
    print("  Phone (same Wi-Fi, laptop hotspot, or USB):")
    for url in phone_urls:
        if "127.0.0.1" in url:
            print(f"    laptop browser also: {url}")
        else:
            print(f"    {url}")
    print()
    print(f"  PIN  {auth.pin[0:3]} {auth.pin[3:6]}")
    print()
    if runner.demo:
        print("  Mode: demo (no Cursor CLI calls)")
    else:
        print(f"  Agent: {runner.agent_bin}")
    print("  Workspaces:")
    for item in workspaces:
        print(f"    - {item['name']}: {item['path']}")
    if scheme == "https":
        print()
        print("  HTTPS uses a self-signed cert. On the phone tap Advanced → Proceed.")
    print()
    print("  USB without Wi-Fi:  adb reverse tcp:%s tcp:%s" % (state.port, state.port))
    print(f"  then open {scheme}://127.0.0.1:{state.port} on the phone.")
    print()
    print("Leave the phone page open to see (and be notified of) a finished run.")
    print("Ctrl+C to stop.")
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.shutdown()
    return 0


def _workspaces(values: list[str]) -> list[dict[str, str]]:
    paths = values or [os.getcwd()]
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in paths:
        path = str(Path(raw).expanduser().resolve())
        if path in seen:
            continue
        if not Path(path).is_dir():
            raise SystemExit(f"Not a directory: {raw}")
        seen.add(path)
        out.append({"name": Path(path).name or path, "path": path})
    return out


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python3 -m cursor_pocket",
        description="Open a local phone UI that sends prompts to Cursor CLI on this laptop.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default 0.0.0.0 for LAN phones)")
    parser.add_argument("--port", type=int, default=8787, help="Port (default 8787)")
    parser.add_argument(
        "--workspace",
        action="append",
        default=[],
        help="Project folder Cursor should edit. Repeat for more than one.",
    )
    parser.add_argument("--name", default="", help="Laptop label shown on the phone")
    parser.add_argument("--pin", default=None, help="Override the 6-digit pairing PIN")
    parser.add_argument("--demo", action="store_true", help="Fake a Cursor run so you can try the phone UI")
    parser.add_argument("--no-force", action="store_true", help="Do not pass --force to agent")
    parser.add_argument("--no-trust", action="store_true", help="Do not pass --trust to agent")
    parser.add_argument(
        "--https",
        action="store_true",
        help="Self-signed HTTPS so Android can install the app and show notifications",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
