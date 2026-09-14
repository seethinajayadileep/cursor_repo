from __future__ import annotations

from openscout.detectors import findings_from_signals
from openscout.models import Snapshot


def test_network_and_console_become_findings() -> None:
    findings = findings_from_signals(
        url="http://127.0.0.1:8765/cart",
        console_errors=[{"type": "error", "text": "Clay analytics: Failed to load product tracker", "url": "http://x"}],
        page_errors=["Express pay SDK missing"],
        network=[{"status": 500, "url": "http://127.0.0.1:8765/api/coupon", "page": "http://127.0.0.1:8765/cart"}],
        snapshot=None,
    )
    kinds = {item.kind for item in findings}
    assert "javascript" in kinds
    assert "console" in kinds
    assert "network" in kinds
    assert any(item.severity == "critical" for item in findings)


def test_missing_alt_is_an_a11y_finding() -> None:
    snapshot = Snapshot(
        url="http://127.0.0.1:8765/",
        title="Home",
        text="Harbor Kiln",
        elements=[],
        images=[{"src": "hero.svg", "alt": None, "hasAlt": False, "visible": True}],
    )
    findings = findings_from_signals(
        url=snapshot.url,
        console_errors=[],
        page_errors=[],
        network=[],
        snapshot=snapshot,
    )
    assert any(item.kind == "a11y" and "alt" in item.title.lower() for item in findings)
