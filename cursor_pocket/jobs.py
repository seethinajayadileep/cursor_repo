"""In-memory job queue. Lives only as long as the laptop daemon."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

TERMINAL = frozenset({"done", "error", "canceled"})


@dataclass
class Job:
    prompt: str
    workspace: str
    workspace_name: str
    mode: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    result: str = ""
    error: str = ""
    duration_ms: int | None = None
    session_id: str | None = None
    follow_up_of: str | None = None
    pid: int | None = None
    model: str | None = None
    chat: str = "current"

    def snapshot(self, include_events: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "prompt": self.prompt,
            "workspace": self.workspace,
            "workspace_name": self.workspace_name,
            "mode": self.mode,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "session_id": self.session_id,
            "follow_up_of": self.follow_up_of,
            "event_count": len(self.events),
            "model": self.model,
            "chat": self.chat,
        }
        if include_events:
            data["events"] = list(self.events)
        return data


class JobStore:
    def __init__(self, limit: int = 80) -> None:
        self.limit = limit
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._cv = threading.Condition()
        self._cancel: dict[str, threading.Event] = {}

    def create(self, **kwargs: Any) -> Job:
        job = Job(**kwargs)
        with self._cv:
            self._jobs[job.id] = job
            self._order.append(job.id)
            self._cancel[job.id] = threading.Event()
            extra = len(self._order) - self.limit
            if extra > 0:
                for old_id in self._order[:extra]:
                    old = self._jobs.get(old_id)
                    if old and old.status in TERMINAL:
                        self._jobs.pop(old_id, None)
                        self._cancel.pop(old_id, None)
                self._order = [jid for jid in self._order if jid in self._jobs]
            self._cv.notify_all()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._cv:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._cv:
            return [self._jobs[jid] for jid in reversed(self._order) if jid in self._jobs]

    def cancel_event(self, job_id: str) -> threading.Event | None:
        with self._cv:
            return self._cancel.get(job_id)

    def request_cancel(self, job_id: str) -> bool:
        with self._cv:
            job = self._jobs.get(job_id)
            flag = self._cancel.get(job_id)
            if not job or job.status in TERMINAL:
                return False
            if flag:
                flag.set()
            if job.status == "queued":
                job.status = "canceled"
                job.finished_at = time.time()
                job.error = "Canceled before start"
                self._append_locked(job, {"kind": "status", "text": "Canceled"})
            self._cv.notify_all()
            return True

    def mutate(self, job_id: str, fn: Callable[[Job], None]) -> Job | None:
        with self._cv:
            job = self._jobs.get(job_id)
            if not job:
                return None
            fn(job)
            self._cv.notify_all()
            return job

    def append(self, job_id: str, event: dict[str, Any]) -> None:
        with self._cv:
            job = self._jobs.get(job_id)
            if not job:
                return
            self._append_locked(job, event)
            self._cv.notify_all()

    def wait_events(self, job_id: str, cursor: int, timeout: float = 1.0) -> tuple[Job | None, list[dict[str, Any]]]:
        deadline = time.time() + timeout
        with self._cv:
            while True:
                job = self._jobs.get(job_id)
                if not job:
                    return None, []
                if len(job.events) > cursor:
                    return job, list(job.events[cursor:])
                if job.status in TERMINAL:
                    return job, []
                remaining = deadline - time.time()
                if remaining <= 0:
                    return job, []
                self._cv.wait(remaining)

    def _append_locked(self, job: Job, event: dict[str, Any]) -> None:
        payload = dict(event)
        payload.setdefault("ts", time.time())
        job.events.append(payload)
        if payload.get("kind") == "result" and payload.get("text") and not job.result:
            job.result = str(payload["text"])
        if payload.get("session_id"):
            job.session_id = str(payload["session_id"])
