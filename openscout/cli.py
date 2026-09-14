from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from openscout import __version__
from openscout.config import load_settings
from openscout.explorer import explore
from openscout.planner import load_journey, parse_journey
from openscout.runner import run_journey


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="openscout",
        description="OpenScout — open-source testing agent for web apps.",
    )
    parser.add_argument("--version", action="version", version=f"OpenScout {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Execute a plain-English / Gherkin journey")
    run_p.add_argument("journey", help="Path to a .feature file or '-' for stdin")
    run_p.add_argument("--url", required=True, help="Base URL of the app under test")
    _add_common(run_p)

    explore_p = sub.add_parser("explore", help="Crawl the app and report bugs")
    explore_p.add_argument("--url", required=True, help="Base URL of the app under test")
    explore_p.add_argument("--goal", default=None, help="Optional text to stop on when visible")
    explore_p.add_argument("--max-steps", type=int, default=None)
    _add_common(explore_p)

    gen_p = sub.add_parser("generate", help="Run a journey and print a Playwright test")
    gen_p.add_argument("journey")
    gen_p.add_argument("--url", required=True)
    gen_p.add_argument("-o", "--output", default=None)
    _add_common(gen_p)

    demo_p = sub.add_parser("demo", help="Start the Harbor Kiln demo shop")
    demo_p.add_argument("--host", default="127.0.0.1")
    demo_p.add_argument("--port", type=int, default=8765)

    serve_p = sub.add_parser("serve", help="Open the OpenScout dashboard")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--no-demo", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "demo":
        _serve_demo(args.host, args.port)
        return
    if args.cmd == "serve":
        from openscout.serve import run_server

        run_server(args.host, args.port, with_demo=not args.no_demo)
        return

    settings = load_settings(
        headless=not getattr(args, "headed", False),
        output_dir=Path(args.output_dir),
        max_steps=getattr(args, "max_steps", None) or None,
    )
    if args.cmd == "run":
        journey = _read_journey(args.journey)
        report = asyncio.run(run_journey(journey, args.url, settings))
        _print_report(report)
        sys.exit(0 if report.status == "passed" else 1)
    if args.cmd == "explore":
        if args.max_steps:
            settings.max_steps = args.max_steps
        report = asyncio.run(explore(args.url, settings, goal=args.goal))
        _print_report(report)
        sys.exit(0 if report.status != "error" else 1)
    if args.cmd == "generate":
        journey = _read_journey(args.journey)
        report = asyncio.run(run_journey(journey, args.url, settings))
        if not report.generated_test:
            print("Journey did not pass; no test generated.", file=sys.stderr)
            _print_report(report)
            sys.exit(1)
        if args.output:
            Path(args.output).write_text(report.generated_test, encoding="utf-8")
            print(args.output)
        else:
            print(report.generated_test)
        sys.exit(0)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--headed", action="store_true", help="Show the browser")
    parser.add_argument("--output-dir", default="runs", help="Where to write reports")


def _read_journey(path: str):
    if path == "-":
        return parse_journey(sys.stdin.read(), source="stdin")
    return load_journey(path)


def _print_report(report) -> None:
    data = report.to_dict()
    summary = data["summary"]
    print(f"OpenScout {report.id}  {report.mode}  {report.status}")
    print(f"steps {summary['passed_steps']}/{summary['steps']}  findings {summary['findings']}")
    for step in report.steps:
        mark = "ok" if step.status == "passed" else "xx"
        print(f"  [{mark}] {step.raw or step.action.type}: {step.message}")
    for finding in report.findings:
        print(f"  !! [{finding.severity}] {finding.title}: {finding.detail}")
    print(f"report: {Path(report.output_dir) / 'report.html'}")
    if report.error:
        print("error:", report.error)


def _serve_demo(host: str, port: int) -> None:
    import uvicorn
    from openscout.demo import app

    print(f"Harbor Kiln demo shop on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def dumps(report) -> str:
    return json.dumps(report.to_dict(), indent=2)
