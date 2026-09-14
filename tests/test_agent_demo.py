from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn

from openscout.config import load_settings
from openscout.demo import app as demo_app
from openscout.explorer import explore
from openscout.planner import load_journey
from openscout.runner import run_journey


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(scope="session")
def shop_url() -> str:
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(demo_app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            if httpx.get(f"{url}/health", timeout=0.4).json().get("ok"):
                break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError("demo shop did not start")
    yield url
    server.should_exit = True


@pytest.mark.asyncio
async def test_guest_checkout_passes(shop_url: str, tmp_path) -> None:
    pytest.importorskip("playwright")
    journey = load_journey("journeys/guest_checkout.feature")
    settings = load_settings(output_dir=tmp_path, headless=True)
    report = await run_journey(journey, shop_url, settings, output_dir=tmp_path)
    assert report.status == "passed", [step.message for step in report.steps if step.status == "failed"]
    assert report.generated_test and "Place order" in report.generated_test


@pytest.mark.asyncio
async def test_broken_careers_journey_fails(shop_url: str, tmp_path) -> None:
    pytest.importorskip("playwright")
    journey = load_journey("journeys/careers_broken.feature")
    settings = load_settings(output_dir=tmp_path, headless=True)
    report = await run_journey(journey, shop_url, settings, output_dir=tmp_path)
    assert report.status == "failed"
    assert any(finding.kind == "network" and "404" in finding.title for finding in report.findings)


@pytest.mark.asyncio
async def test_explore_finds_seeded_bugs(shop_url: str, tmp_path) -> None:
    pytest.importorskip("playwright")
    settings = load_settings(output_dir=tmp_path, headless=True, max_steps=22)
    report = await explore(shop_url, settings, output_dir=tmp_path)
    assert report.status != "error", report.error
    blob = " ".join(f"{item.title} {item.detail} {item.kind} {item.url}" for item in report.findings).lower()
    kinds = {item.kind for item in report.findings}
    assert report.findings, "explore should report at least one finding"
    assert "a11y" in kinds
    functional = (
        "404" in blob
        or "500" in blob
        or "product tracker" in blob
        or "express pay" in blob
        or "/careers" in blob
        or "/api/coupon" in blob
    )
    assert functional, blob
    assert kinds & {"network", "console", "javascript"}
