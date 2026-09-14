from __future__ import annotations

from urllib.parse import urlparse

from openscout.models import Finding, Snapshot


def _host(url: str) -> str:
    return urlparse(url).netloc


def findings_from_signals(
    *,
    url: str,
    console_errors: list[dict],
    page_errors: list[str],
    network: list[dict],
    snapshot: Snapshot | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()

    for err in page_errors:
        key = f"js:{err}"
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                id=f"js-{len(findings)+1}",
                severity="critical",
                kind="javascript",
                title="Unhandled page error",
                detail=err,
                url=url,
            )
        )

    for item in console_errors:
        text = item.get("text") or ""
        key = f"console:{text}"
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                id=f"console-{len(findings)+1}",
                severity="major",
                kind="console",
                title="Browser console error",
                detail=text,
                url=item.get("url") or url,
            )
        )

    for item in network:
        status = item.get("status")
        failed_url = item.get("url") or ""
        key = f"http:{status}:{failed_url}"
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                id=f"http-{len(findings)+1}",
                severity="critical" if status >= 500 else "major",
                kind="network",
                title=f"HTTP {status}",
                detail=failed_url,
                url=item.get("page") or url,
            )
        )

    if snapshot:
        findings.extend(accessibility_findings(snapshot))
        if len((snapshot.text or "").strip()) < 40:
            findings.append(
                Finding(
                    id="empty-page",
                    severity="major",
                    kind="content",
                    title="Page has almost no visible text",
                    detail=f"Only {len((snapshot.text or '').strip())} characters rendered.",
                    url=snapshot.url,
                )
            )
    return findings


def accessibility_findings(snapshot: Snapshot) -> list[Finding]:
    findings: list[Finding] = []
    for index, image in enumerate(snapshot.images):
        if not image.get("visible"):
            continue
        if image.get("hasAlt"):
            continue
        findings.append(
            Finding(
                id=f"a11y-img-{index}",
                severity="minor",
                kind="a11y",
                title="Image is missing an alt attribute",
                detail=image.get("src") or "(inline image)",
                url=snapshot.url,
            )
        )

    for element in snapshot.elements:
        if element.tag not in {"button", "a"} and element.role not in {"button", "link"}:
            continue
        if element.type in {"hidden"}:
            continue
        if element.accessible_name.strip():
            continue
        findings.append(
            Finding(
                id=f"a11y-name-{element.id}",
                severity="minor",
                kind="a11y",
                title="Interactive control has no accessible name",
                detail=f"<{element.tag} type={element.type or '-'}> at ({int(element.x)}, {int(element.y)})",
                url=snapshot.url,
            )
        )
    return findings


def same_origin(base: str, other: str) -> bool:
    return _host(base) == _host(other)
