"""python3 -m cursor_pocket — start the laptop daemon."""

from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

from . import __app_name__, __version__
from .apk import apk_path
from .auth import Auth
from .desktop import desktop_available
from .jobs import JobStore
from .net import public_base_urls
from .runner import Runner, find_agent
from .server import PocketHTTPServer, PocketState
from .tls import wrap_https
from .tunnel import start_tunnel


def resolve_demo(
    demo: bool,
    *,
    fake: bool = False,
    cursor_installed: bool | None = None,
) -> tuple[bool, str]:
    """`--demo` fakes a run only when Cursor is not installed.

    On a Mac that already has Cursor.app, people keep `--demo` from the first-test
    snippet and then the phone says DEMO while Send does nothing. Ignore `--demo`
    in that case so Cloud/Agent actually click Cursor. `--fake` still fakes.
    """
    if fake:
        return True, ""
    if not demo:
        return False, ""
    installed = desktop_available() if cursor_installed is None else cursor_installed
    if installed:
        return (
            False,
            "You passed --demo, but Cursor is installed — sending to Cursor for real "
            "(phone badge will say live, not demo). Pass --fake only to test the phone UI.",
        )
    return True, ""


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    args = _parse(argv)
    demo, demo_note = resolve_demo(args.demo, fake=args.fake)
    if demo_note:
        print(demo_note, file=sys.stderr)
        print(file=sys.stderr)
    workspaces = _workspaces(args.workspace)
    target = "cli" if args.cli else "desktop"
    agent = None if demo or target == "desktop" else find_agent()
    if not demo and target == "cli" and not agent:
        print(
            "No Cursor CLI (`agent`) found on PATH.\n"
            "Install it from https://cursor.com/docs/cli/overview\n"
            "or omit --cli to drive the Cursor desktop app instead.\n",
            file=sys.stderr,
        )
        return 2
    if not demo and target == "desktop" and not desktop_available():
        print(
            "Cursor desktop was not found. Install Cursor on this Mac, open your project,\n"
            "or pass --cli to use Cursor CLI, or --demo to try the phone UI.\n",
            file=sys.stderr,
        )
        return 2

    auth = Auth.generate(args.pin)
    runner = Runner(
        demo=demo,
        force=not args.no_force,
        trust=not args.no_trust,
        agent_bin=agent or find_agent(),
        target=target,
    )
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
    if args.https and args.online:
        print("Ignoring --https: --online already gives the phone a real HTTPS URL.", file=sys.stderr)
    elif args.https:
        wrap_https(httpd)
        scheme = "https"
    state.port = httpd.server_address[1]
    urls = public_base_urls(args.host, state.port)
    phone_urls = [u.replace("http://", f"{scheme}://", 1) for u in urls]
    host_url = f"{scheme}://127.0.0.1:{state.port}/host"

    tunnel = None
    if args.online:
        print("Opening an internet tunnel so the phone can connect from another network…")
        tunnel = start_tunnel(state.port)
        state.online_url = tunnel.url

    print()
    print(f"{__app_name__} v{__version__}")
    if state.online_url:
        print("Phone remote for Cursor desktop. Laptop and phone both use the internet.")
    else:
        print("Phone remote for Cursor desktop. Keep Cursor open on this Mac.")
        print("Need the phone on another network? Rerun with --online.")
    print("Keep this window open, keep the Mac awake and unlocked, and leave Cursor running.")
    print()
    print(f"  Laptop pairing page: {host_url}")
    if state.online_url:
        print()
        print(f"  Phone (any network with internet):  {state.online_url}")
        print("  Scan the QR on the laptop pairing page, or paste that URL in Chrome.")
        print("  Anyone who has the URL still needs the PIN.")
    print("  Phone (same Wi-Fi, laptop hotspot, or USB):")
    for url in phone_urls:
        if "127.0.0.1" in url:
            print(f"    laptop browser also: {url}")
        else:
            print(f"    {url}")
    print()
    print(f"  PIN  {auth.pin[0:3]} {auth.pin[3:6]}")
    if apk_path():
        print(f"  Android APK: {scheme}://127.0.0.1:{state.port}/apk/cursor-pocket.apk")
        print("  Open that on the phone (or the Install Android app button) and sideload it.")
    print()
    if runner.demo:
        print("  Mode: DEMO — Cursor will NOT run. This only tests the phone UI.")
        print("  To actually click Send in Cursor, stop this (Ctrl+C) and rerun without --demo.")
    elif runner.target == "desktop":
        print("  Target: Cursor desktop — Agent = IDE Cmd+I, Cloud = Agents Window (File → New Agents Window) + Cloud picker")
        print("  Grant Accessibility to Terminal/Python in macOS Settings.")
    else:
        print(f"  Agent CLI: {runner.agent_bin}")
    if tunnel:
        print(f"  Tunnel: {tunnel.kind}")
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
    finally:
        if tunnel:
            tunnel.stop()
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
        description="Phone remote that pastes prompts into Cursor desktop on this Mac.",
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
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Fake a run if Cursor is not installed. Ignored on a Mac that has Cursor (use --fake to fake anyway).",
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Always fake the run (phone says demo). Cursor is not clicked.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Use Cursor CLI (`agent`) instead of clicking Send in the desktop app",
    )
    parser.add_argument("--no-force", action="store_true", help="Do not pass --force to agent (CLI mode only)")
    parser.add_argument("--no-trust", action="store_true", help="Do not pass --trust to agent")
    parser.add_argument(
        "--https",
        action="store_true",
        help="Self-signed HTTPS so Android can install the app and show notifications",
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="Give the phone a public HTTPS URL (cloudflared or ngrok). Both devices need internet.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
