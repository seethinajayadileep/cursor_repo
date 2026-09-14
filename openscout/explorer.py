from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from openscout.browser import BrowserSession
from openscout.config import Settings
from openscout.detectors import findings_from_signals, same_origin
from openscout.llm import choose_explore_action, llm_available
from openscout.matcher import fill_value_for, is_skippable, suggest_locator
from openscout.models import Action, Element, RunReport, Snapshot, StepResult
from openscout.report import write_reports

GENERIC_NAV = {"shop", "cart", "contact", "careers", "home", "harbor kiln"}


def _abs_href(page_url: str, element: Element) -> str | None:
    href = (element.href or "").strip()
    if not href or href.startswith("#") or href.lower().startswith("javascript"):
        return None
    return urljoin(page_url, href)


def _path(url: str) -> str:
    return urlparse(url).path or "/"


def _nav_name(element: Element) -> str:
    return (element.accessible_name or "").lower().split("(")[0].strip()


def _action_key(url: str, element: Element) -> str:
    target = _abs_href(url, element)
    if target:
        return f"goto:{_path(target)}"
    return f"onpage:{_path(url)}|{element.tag}|{element.type}|{element.accessible_name}|{element.name}"


def _priority(element: Element, page_url: str, visited_paths: set[str]) -> int:
    name = _nav_name(element)
    target = _abs_href(page_url, element)
    if target:
        path = _path(target)
        if not same_origin(page_url, target):
            return -50
        if path in visited_paths:
            return -40
        if name in GENERIC_NAV:
            return 8
        return 28

    score = 8
    if element.tag in {"input", "textarea"}:
        score += 14
    if element.tag == "button" or element.type in {"submit", "button"}:
        score += 10
    if any(word in name for word in ("add to cart", "coupon", "apply", "express", "place order", "send")):
        score += 18
    return score


def _remember_links(snapshot: Snapshot, frontier: list[str], queued: set[str], visited_paths: set[str]) -> None:
    for element in snapshot.elements:
        target = _abs_href(snapshot.url, element)
        if not target or not same_origin(snapshot.url, target):
            continue
        path = _path(target)
        if path in visited_paths or target in queued:
            continue
        queued.add(target)
        frontier.append(target)


async def explore(
    base_url: str,
    settings: Settings,
    output_dir: Path | None = None,
    goal: str | None = None,
) -> RunReport:
    run_id = uuid.uuid4().hex[:10]
    started = datetime.now(timezone.utc)
    run_dir = Path(output_dir or settings.output_dir) / f"{started.strftime('%Y%m%dT%H%M%S')}-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    report = RunReport(
        id=run_id,
        mode="explore",
        base_url=base_url,
        status="running",
        started_at=started.isoformat(),
        finished_at="",
        output_dir=str(run_dir),
    )
    session = BrowserSession(settings, run_dir)
    await session.start()
    seen_actions: set[str] = set()
    visited_paths: set[str] = {_path(base_url)}
    frontier: list[str] = []
    queued: set[str] = set()
    finding_ids: set[str] = set()
    console_seen = 0
    error_seen = 0
    network_seen = 0

    async def ingest(snapshot: Snapshot | None) -> None:
        nonlocal console_seen, error_seen, network_seen
        console_errors = session.consume_new_console_errors(console_seen)
        page_errors = session.consume_new_page_errors(error_seen)
        network = session.consume_new_network(network_seen)
        console_seen = len(session.console)
        error_seen = len(session.page_errors)
        network_seen = len(session.network)
        url = session.page.url if session.page else base_url
        for finding in findings_from_signals(
            url=url,
            console_errors=console_errors,
            page_errors=page_errors,
            network=network,
            snapshot=snapshot,
        ):
            if finding.id in finding_ids:
                continue
            finding_ids.add(finding.id)
            try:
                finding.screenshot = await session.screenshot(f"finding-{finding.id}.png")
            except Exception:
                finding.screenshot = None
            report.findings.append(finding)

    try:
        await session.goto(base_url)
        snapshot = await session.snapshot()
        await ingest(snapshot)
        _remember_links(snapshot, frontier, queued, visited_paths)
        shot = await session.screenshot("step-00-home.png")
        report.steps.append(
            StepResult(
                index=0,
                raw=f"open {base_url}",
                action=Action(type="open", target=base_url, raw=f"open {base_url}"),
                status="passed",
                message=f"Opened {session.page.url}",
                duration_ms=0,
                screenshot=shot,
                url=session.page.url,
            )
        )

        for index in range(1, settings.max_steps + 1):
            snapshot = await session.snapshot()
            await ingest(snapshot)
            if session.page:
                visited_paths.add(_path(session.page.url))
            _remember_links(snapshot, frontier, queued, visited_paths)

            candidates = [
                el
                for el in snapshot.elements
                if not is_skippable(el) and _action_key(snapshot.url, el) not in seen_actions
            ]
            candidates.sort(key=lambda el: _priority(el, snapshot.url, visited_paths), reverse=True)
            candidates = [el for el in candidates if _priority(el, snapshot.url, visited_paths) > 0]

            picked = None
            if candidates:
                if llm_available(settings):
                    payload = [
                        {
                            "index": i,
                            "name": el.accessible_name,
                            "tag": el.tag,
                            "type": el.type,
                            "href": el.href,
                        }
                        for i, el in enumerate(candidates[:20])
                    ]
                    choice = choose_explore_action(snapshot, payload, settings)
                    if choice is not None:
                        picked = candidates[choice]
                if picked is None:
                    picked = candidates[0]
                seen_actions.add(_action_key(snapshot.url, picked))
                action, ok, message = await _perform(session, snapshot, picked)
            else:
                next_url = None
                while frontier:
                    candidate_url = frontier.pop(0)
                    if _path(candidate_url) not in visited_paths:
                        next_url = candidate_url
                        break
                if not next_url:
                    break
                await session.goto(next_url)
                action = Action(type="open", target=next_url, raw=f"open {next_url}")
                ok, message = True, f"Opened {next_url}"

            shot = await session.screenshot(f"step-{index:02d}.png")
            report.steps.append(
                StepResult(
                    index=index,
                    raw=action.raw,
                    action=action,
                    status="passed" if ok else "failed",
                    message=message,
                    duration_ms=0,
                    screenshot=shot,
                    locator=suggest_locator(action, picked),
                    url=session.page.url if session.page else snapshot.url,
                )
            )
            snapshot = await session.snapshot()
            await ingest(snapshot)
            if session.page:
                visited_paths.add(_path(session.page.url))
            if goal and goal.lower() in (snapshot.text or "").lower():
                report.status = "passed"
                break
            if session.page and not same_origin(base_url, session.page.url):
                await session.goto(base_url)

        report.pages_visited = list(session.pages_visited)
        if report.status == "running":
            report.status = "passed"
        session.dump_signals(run_dir / "signals.json")
        (run_dir / "graph.json").write_text(
            json.dumps({"pages": report.pages_visited, "actions": sorted(seen_actions)}, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        report.status = "error"
        report.error = str(exc)
    finally:
        await session.close()
        report.finished_at = datetime.now(timezone.utc).isoformat()
        write_reports(report, run_dir)
    return report


async def _perform(session: BrowserSession, snapshot: Snapshot, element: Element) -> tuple[Action, bool, str]:
    page = session.page
    assert page
    name = element.accessible_name or element.placeholder or element.name or element.tag
    try:
        if element.tag in {"input", "textarea"} and element.type not in {
            "submit",
            "button",
            "checkbox",
            "radio",
            "hidden",
        }:
            value = fill_value_for(element)
            await session.fill(element.id, value)
            action = Action(type="fill", target=name, value=value, raw=f'fill "{name}" with "{value}"')
            return action, True, f'Filled "{name}"'
        if element.type in {"checkbox", "radio"}:
            await session.check(element.id, True)
            action = Action(type="check", target=name, raw=f'check "{name}"')
            return action, True, f'Checked "{name}"'
        await session.click(element.id)
        action = Action(type="click", target=name, raw=f'click "{name}"')
        return action, True, f'Clicked "{name}"'
    except Exception as exc:
        action = Action(type="click", target=name, raw=f'click "{name}"')
        return action, False, str(exc)
