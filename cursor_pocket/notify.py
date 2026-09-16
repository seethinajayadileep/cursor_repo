"""Laptop (macOS) notification when a Pocket job finishes or fails."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

# Last notice, for tests. (title, body) or None.
LAST: tuple[str, str] | None = None


def notice_for(job: Any) -> tuple[str, str]:
    status = getattr(job, "status", "") or ""
    mode = getattr(job, "mode", "") or ""
    prompt = str(getattr(job, "prompt", "") or "").strip()
    error = str(getattr(job, "error", "") or "").strip()
    if status == "canceled":
        title = "Cursor canceled"
    elif status != "done":
        title = "Cursor failed"
    elif mode == "cloud":
        title = "Cloud Agent finished"
    else:
        title = "Cursor finished"
    body = prompt[:140] if prompt else (error or "Done")
    return title, body


def notify_job(job: Any) -> None:
    global LAST
    title, body = notice_for(job)
    LAST = (title, body)
    _mac(title, body)


def _mac(title: str, body: str) -> None:
    if sys.platform != "darwin":
        return
    t = _escape(title)
    b = _escape(body)
    script = f'display notification "{b}" with title "{t}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
