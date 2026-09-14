from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from openscout.browser import BrowserSession
from openscout.config import Settings
from openscout.detectors import findings_from_signals
from openscout.generator import generate_playwright_test
from openscout.matcher import find_element, suggest_locator
from openscout.models import Action, Journey, RunReport, StepResult
from openscout.planner import parse_journey
from openscout.report import write_reports


async def run_journey(
    journey: Journey,
    base_url: str,
    settings: Settings,
    output_dir: Path | None = None,
) -> RunReport:
    run_id = uuid.uuid4().hex[:10]
    started = datetime.now(timezone.utc)
    run_dir = Path(output_dir or settings.output_dir) / f"{started.strftime('%Y%m%dT%H%M%S')}-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    report = RunReport(
        id=run_id,
        mode="journey",
        base_url=base_url,
        status="running",
        started_at=started.isoformat(),
        finished_at="",
        output_dir=str(run_dir),
    )
    session = BrowserSession(settings, run_dir)
    await session.start()
    console_seen = 0
    error_seen = 0
    network_seen = 0
    try:
        for index, action in enumerate(journey.steps, start=1):
            step = await _run_step(session, action, index, base_url)
            report.steps.append(step)
            snapshot = await session.snapshot()
            console_errors = session.consume_new_console_errors(console_seen)
            page_errors = session.consume_new_page_errors(error_seen)
            network = session.consume_new_network(network_seen)
            console_seen = len(session.console)
            error_seen = len(session.page_errors)
            network_seen = len(session.network)
            new_findings = findings_from_signals(
                url=session.page.url if session.page else base_url,
                console_errors=console_errors,
                page_errors=page_errors,
                network=network,
                snapshot=snapshot,
            )
            for finding in new_findings:
                if finding.id not in {existing.id for existing in report.findings}:
                    if not finding.screenshot:
                        finding.screenshot = await session.screenshot(f"finding-{finding.id}.png")
                    report.findings.append(finding)
            if step.status == "failed":
                report.status = "failed"
                break
        else:
            report.status = "failed" if any(s.status == "failed" for s in report.steps) else "passed"
        report.pages_visited = list(session.pages_visited)
        if report.status == "passed":
            report.generated_test = generate_playwright_test(journey, report, base_url)
            (run_dir / "generated_test.py").write_text(report.generated_test, encoding="utf-8")
        session.dump_signals(run_dir / "signals.json")
    except Exception as exc:
        report.status = "error"
        report.error = str(exc)
    finally:
        await session.close()
        report.finished_at = datetime.now(timezone.utc).isoformat()
        write_reports(report, run_dir)
    return report


async def run_journey_text(text: str, base_url: str, settings: Settings, output_dir: Path | None = None) -> RunReport:
    return await run_journey(parse_journey(text), base_url, settings, output_dir)


async def _run_step(session: BrowserSession, action: Action, index: int, base_url: str) -> StepResult:
    started = time.perf_counter()
    page = session.page
    assert page
    try:
        if action.type == "open":
            target = action.target
            if target in {"/", "home", "the demo shop", "demo shop", "the home page", "home page"}:
                target = base_url
            url = urljoin(base_url if base_url.endswith("/") else base_url + "/", target)
            if target.startswith("http://") or target.startswith("https://"):
                url = target
            await session.goto(url)
            shot = await session.screenshot(f"step-{index:02d}.png")
            return _ok(index, action, started, f"Opened {page.url}", shot, suggest_locator(action, None), page.url)

        if action.type == "wait":
            await session.wait_ms(int(action.value or "500"))
            return _ok(index, action, started, f"Waited {action.value}ms", None, None, page.url)

        if action.type == "screenshot":
            shot = await session.screenshot(f"step-{index:02d}.png")
            return _ok(index, action, started, "Captured screenshot", shot, None, page.url)

        snapshot = await session.snapshot()

        if action.type == "see":
            if normalize_has(snapshot.text, action.target) or normalize_has(snapshot.title, action.target):
                shot = await session.screenshot(f"step-{index:02d}.png")
                return _ok(index, action, started, f'Found "{action.target}"', shot, None, page.url)
            shot = await session.screenshot(f"step-{index:02d}-fail.png")
            return _fail(index, action, started, f'Expected to see "{action.target}"', shot, page.url)

        if action.type == "not_see":
            if normalize_has(snapshot.text, action.target):
                shot = await session.screenshot(f"step-{index:02d}-fail.png")
                return _fail(index, action, started, f'Did not expect "{action.target}"', shot, page.url)
            return _ok(index, action, started, f'"{action.target}" is absent', None, None, page.url)

        if action.type == "url_contains":
            if action.target.lower() in page.url.lower():
                return _ok(index, action, started, page.url, None, None, page.url)
            shot = await session.screenshot(f"step-{index:02d}-fail.png")
            return _fail(index, action, started, f"URL {page.url} does not contain {action.target}", shot, page.url)

        if action.type == "url_is":
            if page.url.rstrip("/") == action.target.rstrip("/"):
                return _ok(index, action, started, page.url, None, None, page.url)
            shot = await session.screenshot(f"step-{index:02d}-fail.png")
            return _fail(index, action, started, f"URL was {page.url}", shot, page.url)

        if action.type == "title_contains":
            if action.target.lower() in snapshot.title.lower():
                return _ok(index, action, started, snapshot.title, None, None, page.url)
            return _fail(index, action, started, f'Title was "{snapshot.title}"', None, page.url)

        if action.type == "title_is":
            if snapshot.title == action.target:
                return _ok(index, action, started, snapshot.title, None, None, page.url)
            return _fail(index, action, started, f'Title was "{snapshot.title}"', None, page.url)

        if action.type == "no_console":
            errors = [item for item in session.console if item.get("type") in {"error", "assert"}]
            if errors:
                return _fail(index, action, started, errors[-1]["text"], None, page.url)
            return _ok(index, action, started, "No console errors", None, None, page.url)

        element = find_element(snapshot, action.target, action.type)
        if element is None:
            shot = await session.screenshot(f"step-{index:02d}-fail.png")
            return _fail(
                index,
                action,
                started,
                f'Could not find "{action.target}" among {len(snapshot.elements)} controls',
                shot,
                page.url,
            )

        locator = suggest_locator(action, element)
        if action.type == "click":
            await session.click(element.id)
        elif action.type == "fill":
            await session.fill(element.id, action.value)
        elif action.type == "select":
            await session.select(element.id, action.value)
        elif action.type == "check":
            await session.check(element.id, True)
        elif action.type == "uncheck":
            await session.check(element.id, False)
        else:
            return _fail(index, action, started, f"Unknown action {action.type}", None, page.url)

        shot = await session.screenshot(f"step-{index:02d}.png")
        return _ok(index, action, started, f'{action.type} "{action.target}"', shot, locator, page.url)
    except Exception as exc:
        shot = None
        try:
            shot = await session.screenshot(f"step-{index:02d}-fail.png")
        except Exception:
            pass
        return _fail(index, action, started, str(exc), shot, page.url if page else "")


def normalize_has(haystack: str, needle: str) -> bool:
    return (needle or "").lower() in (haystack or "").lower()


def _ok(index: int, action: Action, started: float, message: str, shot: str | None, locator: str | None, url: str) -> StepResult:
    return StepResult(
        index=index,
        raw=action.raw,
        action=action,
        status="passed",
        message=message,
        duration_ms=int((time.perf_counter() - started) * 1000),
        screenshot=shot,
        locator=locator,
        url=url,
    )


def _fail(index: int, action: Action, started: float, message: str, shot: str | None, url: str) -> StepResult:
    return StepResult(
        index=index,
        raw=action.raw,
        action=action,
        status="failed",
        message=message,
        duration_ms=int((time.perf_counter() - started) * 1000),
        screenshot=shot,
        url=url,
    )
