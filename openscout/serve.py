from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from openscout.config import load_settings
from openscout.explorer import explore
from openscout.planner import parse_journey
from openscout.runner import run_journey

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
RUNS = Path("runs")
RUNS.mkdir(exist_ok=True)
JOBS: dict[str, dict[str, Any]] = {}
LOCK = asyncio.Lock()

app = FastAPI(title="OpenScout")
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


class RunRequest(BaseModel):
    url: str
    mode: str = Field(pattern="^(journey|explore)$")
    journey: str = ""
    goal: str | None = None
    max_steps: int = 20
    headed: bool = False


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "agent": "openscout"}


@app.get("/api/sample-journey")
def sample_journey() -> dict:
    path = ROOT.parent / "journeys" / "guest_checkout.feature"
    if not path.exists():
        path = ROOT / "journeys" / "guest_checkout.feature"
    text = path.read_text(encoding="utf-8") if path.exists() else DEFAULT_JOURNEY
    return {"text": text}


@app.post("/api/runs")
async def start_run(payload: RunRequest) -> dict:
    settings = load_settings(headless=not payload.headed, max_steps=payload.max_steps, output_dir=RUNS)
    job_id = __import__("uuid").uuid4().hex[:10]
    JOBS[job_id] = {"id": job_id, "status": "running", "report": None, "error": None}
    asyncio.create_task(_execute(job_id, payload, settings))
    return {"id": job_id, "status": "running"}


@app.get("/api/runs/{job_id}")
def get_run(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown run")
    return job


@app.get("/runs/{run_id}/{rest:path}")
def run_file(run_id: str, rest: str) -> FileResponse:
    path = (RUNS / run_id / rest).resolve()
    if not str(path).startswith(str(RUNS.resolve())) or not path.exists():
        raise HTTPException(404, "Missing artifact")
    return FileResponse(path)


async def _execute(job_id: str, payload: RunRequest, settings) -> None:
    async with LOCK:
        try:
            if payload.mode == "explore":
                report = await explore(payload.url, settings, goal=payload.goal)
            else:
                journey = parse_journey(payload.journey or DEFAULT_JOURNEY)
                report = await run_journey(journey, payload.url, settings)
            payload_report = report.to_dict()
            payload_report["run_folder"] = Path(report.output_dir).name
            JOBS[job_id] = {
                "id": job_id,
                "status": report.status,
                "report": payload_report,
                "error": report.error,
            }
        except Exception as exc:
            JOBS[job_id] = {"id": job_id, "status": "error", "report": None, "error": str(exc)}


def run_server(host: str, port: int, with_demo: bool = True) -> None:
    import uvicorn

    if with_demo:
        demo_thread = threading.Thread(target=_run_demo, kwargs={"host": host}, daemon=True)
        demo_thread.start()
        print(f"Harbor Kiln demo shop on http://{host}:8765")
    print(f"OpenScout dashboard on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def _run_demo(host: str) -> None:
    import uvicorn
    from openscout.demo import app as demo_app

    uvicorn.run(demo_app, host=host, port=8765, log_level="warning")


DEFAULT_JOURNEY = """Feature: Guest checkout
  Scenario: Buy the red mug
    Given I open the home page
    When I click "Shop"
    And I click "Red Mug"
    And I click "Add to cart"
    And I click "Cart"
    And I fill "Full name" with "Ada Lovelace"
    And I fill "Email" with "ada@example.com"
    And I click "Place order"
    Then I should see "Order confirmed"
"""
