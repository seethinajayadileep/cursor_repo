"""Small FastAPI app: upload a PDF, download a redacted .docx."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from redact.evaluate import evaluate_pages, render_report
from redact.pipeline import redact_document

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "uploads"
OUTPUT_DIR = ROOT / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PII Redaction Tool")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

JOBS: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


@app.post("/redact")
async def redact(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "upload.pdf").suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(400, "Please upload a PDF or .txt file.")

    job_id = uuid.uuid4().hex[:12]
    source = UPLOAD_DIR / f"{job_id}{suffix}"
    source.write_bytes(await file.read())
    docx_path = OUTPUT_DIR / f"{job_id}_redacted.docx"

    result = redact_document(source, docx_path)
    metrics = None
    report_path = OUTPUT_DIR / f"{job_id}_evaluation.md"
    try:
        metrics = evaluate_pages(result.original_pages)
        report_path.write_text(render_report(metrics), encoding="utf-8")
    except Exception:
        metrics = None
        report_path = None

    JOBS[job_id] = {
        "docx": str(docx_path),
        "report": str(report_path) if report_path else None,
        "counts": result.counts,
        "metrics": {
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "accuracy": metrics["accuracy"],
        }
        if metrics
        else None,
    }
    return {
        "job_id": job_id,
        "filename": file.filename,
        "counts": result.counts,
        "metrics": JOBS[job_id]["metrics"],
        "mapping_preview": dict(list(result.mapping.items())[:12]),
    }


@app.get("/download/docx/{job_id}")
def download_docx(job_id: str) -> FileResponse:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job.")
    path = Path(job["docx"])
    if not path.exists():
        raise HTTPException(404, "File missing.")
    return FileResponse(
        path,
        filename="redacted.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/download/report/{job_id}")
def download_report(job_id: str) -> FileResponse:
    job = JOBS.get(job_id)
    if not job or not job.get("report"):
        raise HTTPException(404, "No report for this job.")
    path = Path(job["report"])
    if not path.exists():
        raise HTTPException(404, "Report missing.")
    return FileResponse(path, filename="evaluation_report.md", media_type="text/markdown")
