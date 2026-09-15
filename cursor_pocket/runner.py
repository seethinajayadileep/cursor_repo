"""Run Cursor CLI (`agent`) on the laptop, or a demo stand-in."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from typing import Any

from .changes import describe_changes, snapshot
from .desktop import (
    copy_prompt,
    desktop_available,
    focus_cursor,
    open_workspace,
    read_cursor_text,
    request_stop,
    send_prompt,
)
from .jobs import Job, JobStore
from .notify import notify_job
from .parse import parse_stream_line

AGENT_CANDIDATES = (
    "agent",
    os.path.expanduser("~/.local/bin/agent"),
    os.path.expanduser("~/AppData/Local/cursor-agent/agent.exe"),
)


def find_agent() -> str | None:
    for candidate in AGENT_CANDIDATES:
        path = shutil.which(candidate) if os.path.sep not in candidate else candidate
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        if os.path.sep not in candidate:
            which = shutil.which(candidate)
            if which:
                return which
    return None


class Runner:
    def __init__(
        self,
        *,
        demo: bool = False,
        force: bool = True,
        trust: bool = True,
        agent_bin: str | None = None,
        target: str = "desktop",
        idle_seconds: float = 18.0,
        max_seconds: float = 45 * 60,
        poll_seconds: float = 2.0,
        open_delay: float = 1.2,
        after_send_delay: float = 2.0,
        no_activity_seconds: float = 180.0,
    ) -> None:
        self.demo = demo
        self.force = force
        self.trust = trust
        self.agent_bin = agent_bin or find_agent()
        self.target = target
        self.idle_seconds = idle_seconds
        self.max_seconds = max_seconds
        self.poll_seconds = poll_seconds
        self.open_delay = open_delay
        self.after_send_delay = after_send_delay
        self.no_activity_seconds = no_activity_seconds
        self._serial = threading.Lock()

    def available(self) -> bool:
        if self.demo:
            return True
        if self.target == "desktop":
            return desktop_available()
        return bool(self.agent_bin)

    def start(self, store: JobStore, job: Job) -> None:
        thread = threading.Thread(target=self._queued_run, args=(store, job), daemon=True, name=f"job-{job.id}")
        thread.start()

    def _queued_run(self, store: JobStore, job: Job) -> None:
        # One Cursor CLI process at a time so two phone prompts cannot clobber the same repo.
        with self._serial:
            current = store.get(job.id)
            cancel = store.cancel_event(job.id)
            if not current or current.status == "canceled" or (cancel and cancel.is_set()):
                return
            self._run(store, job)

    def _run(self, store: JobStore, job: Job) -> None:
        cancel = store.cancel_event(job.id)
        store.mutate(
            job.id,
            lambda j: (
                setattr(j, "status", "running"),
                setattr(j, "started_at", time.time()),
            ),
        )
        store.append(job.id, {"kind": "status", "text": "Running on the laptop"})
        try:
            if self.demo:
                self._run_demo(store, job, cancel)
            elif self.target == "desktop":
                self._run_desktop(store, job, cancel)
            else:
                self._run_agent(store, job, cancel)
        except Exception as exc:  # noqa: BLE001 — surface any runner crash to the phone
            store.mutate(
                job.id,
                lambda j: (
                    setattr(j, "status", "error"),
                    setattr(j, "error", str(exc)),
                    setattr(j, "finished_at", time.time()),
                ),
            )
            store.append(job.id, {"kind": "error", "text": str(exc)})

    def _run_demo(self, store: JobStore, job: Job, cancel: threading.Event | None) -> None:
        steps = [
            {"kind": "system", "text": f"Demo mode · {job.workspace_name}", "model": "demo"},
            {"kind": "assistant", "text": "Got it. I'll pretend to work through this on the laptop.\n"},
            {"kind": "tool", "text": f"read started · {job.workspace}", "tool": "read", "subtype": "started"},
            {"kind": "tool", "text": "read done", "tool": "read", "subtype": "done"},
            {
                "kind": "assistant",
                "text": (
                    f"{'Cursor Cloud Agent' if job.mode == 'cloud' else 'Cursor desktop'} would answer here.\n\nPrompt:\n{job.prompt.strip()}\n\n"
                    "Demo only — no files were edited."
                ),
            },
            {
                "kind": "changes",
                "text": "What was fixed:\n  • (demo) no real files changed",
            },
        ]
        for step in steps:
            if cancel and cancel.is_set():
                self._finish(store, job, "canceled", error="Canceled from the phone")
                return
            time.sleep(0.45)
            store.append(job.id, step)
        result = steps[-1]["text"]
        store.append(
            job.id,
            {
                "kind": "result",
                "text": result,
                "error": False,
                "duration_ms": int(((time.time() - (job.started_at or time.time())) * 1000)),
                "session_id": f"demo-{job.id}",
            },
        )
        self._finish(store, job, "done", result=result)

    def _run_desktop(self, store: JobStore, job: Job, cancel: threading.Event | None) -> None:
        if not desktop_available():
            raise RuntimeError("Open Cursor desktop on this Mac and grant Accessibility to Terminal/Python.")
        before = snapshot(job.workspace)
        cloud = job.mode == "cloud"
        if cloud:
            store.append(
                job.id,
                {
                    "kind": "system",
                    "text": f"Using the Cursor window in front · Cloud · {job.workspace_name}",
                },
            )
            focus_cursor()
        else:
            store.append(job.id, {"kind": "system", "text": f"Opening Cursor desktop · {job.workspace_name}"})
            open_workspace(job.workspace)
        if self.open_delay:
            time.sleep(self.open_delay)
        if cancel and cancel.is_set():
            self._finish(store, job, "canceled", error="Canceled from the phone")
            return
        copy_prompt(job.prompt)
        send_prompt(kind="cloud" if cloud else "agent", new_chat=not bool(job.follow_up_of))
        where = "Cloud in the open Cursor window" if cloud else "Cursor desktop"
        sid = f"{'cloud' if cloud else 'desktop'}-{job.id}"
        store.append(job.id, {"kind": "status", "text": f"Sent to {where} — waiting for the reply and file fixes"})
        store.mutate(job.id, lambda j: setattr(j, "session_id", sid))
        if self.after_send_delay:
            time.sleep(self.after_send_delay)
        baseline_ax = read_cursor_text()

        started = time.time()
        last_change = started
        last_ax = baseline_ax
        last_git = before
        saw_activity = False
        while True:
            if cancel and cancel.is_set():
                request_stop()
                self._finish(store, job, "canceled", error="Canceled from the phone")
                return
            now = time.time()
            if now - started > self.max_seconds:
                summary = describe_changes(job.workspace, before)
                ax = read_cursor_text()
                result = _desktop_result(_new_text(baseline_ax, ax), summary)
                store.append(job.id, {"kind": "changes", "text": str(summary["text"])})
                self._finish(store, job, "done", result=result)
                return

            ax = read_cursor_text()
            if ax and ax != last_ax:
                last_ax = ax
                last_change = now
                grew = _new_text(baseline_ax, ax)
                if grew.strip():
                    saw_activity = True
                    store.append(job.id, {"kind": "assistant", "text": grew[-4000:], "delta": False})

            git_now = snapshot(job.workspace)
            if git_now != last_git:
                last_git = git_now
                last_change = now
                saw_activity = True
                summary = describe_changes(job.workspace, before)
                store.append(job.id, {"kind": "changes", "text": str(summary["text"])})

            quiet = now - last_change
            if saw_activity and quiet >= self.idle_seconds:
                summary = describe_changes(job.workspace, before)
                grew = _new_text(baseline_ax, last_ax or read_cursor_text())
                if summary["text"]:
                    store.append(job.id, {"kind": "changes", "text": str(summary["text"])})
                result = _desktop_result(grew, summary)
                store.append(
                    job.id,
                    {
                        "kind": "result",
                        "text": result,
                        "error": False,
                        "session_id": sid,
                    },
                )
                self._finish(store, job, "done", result=result)
                return
            if not saw_activity and now - started > self.no_activity_seconds:
                summary = describe_changes(job.workspace, before)
                grew = _new_text(baseline_ax, read_cursor_text())
                note = (
                    "Cursor may still be running, but the chat panel could not be read. "
                    "Enable Accessibility for Terminal/Python. File changes are below."
                )
                store.append(job.id, {"kind": "assistant", "text": grew or note})
                store.append(job.id, {"kind": "changes", "text": str(summary["text"])})
                result = _desktop_result(grew or note, summary)
                self._finish(store, job, "done", result=result)
                return
            if self.poll_seconds:
                time.sleep(self.poll_seconds)

    def _run_agent(self, store: JobStore, job: Job, cancel: threading.Event | None) -> None:
        cmd = [
            self.agent_bin or "agent",
            "-p",
            "--output-format",
            "stream-json",
            "--stream-partial-output",
            "--workspace",
            job.workspace,
        ]
        if self.trust:
            cmd.append("--trust")
        if self.force and job.mode == "agent":
            cmd.append("--force")
        if job.mode in {"ask", "plan"}:
            cmd.extend(["--mode", job.mode])
        if job.model:
            cmd.extend(["--model", job.model])
        if job.session_id and job.follow_up_of:
            cmd.extend(["--resume", job.session_id])
        cmd.append(job.prompt)

        env = os.environ.copy()
        # Headless: never wait for a TTY prompt.
        env.setdefault("CI", "1")

        creationflags = 0
        preexec_fn = None
        if os.name == "posix":
            preexec_fn = os.setsid  # type: ignore[assignment]
        elif os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        proc = subprocess.Popen(  # noqa: S603 — user-configured agent binary
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=job.workspace,
            env=env,
            text=True,
            bufsize=1,
            creationflags=creationflags,
            preexec_fn=preexec_fn,
        )
        store.mutate(job.id, lambda j: setattr(j, "pid", proc.pid))

        killer = threading.Thread(target=self._watch_cancel, args=(proc, cancel), daemon=True)
        killer.start()

        assert proc.stdout is not None
        result_text = ""
        error_text = ""
        for line in proc.stdout:
            event = parse_stream_line(line)
            if not event:
                continue
            store.append(job.id, event)
            if event.get("kind") == "result":
                result_text = str(event.get("text") or "")
                if event.get("error"):
                    error_text = result_text
            if event.get("kind") == "error":
                error_text = str(event.get("text") or error_text)

        code = proc.wait()
        if cancel and cancel.is_set():
            self._finish(store, job, "canceled", error="Canceled from the phone")
            return
        if code != 0:
            msg = error_text or f"Cursor CLI exited with code {code}"
            self._finish(store, job, "error", error=msg, result=result_text)
            return
        self._finish(store, job, "done", result=result_text)

    def _watch_cancel(self, proc: subprocess.Popen[str], cancel: threading.Event | None) -> None:
        if not cancel:
            return
        while proc.poll() is None:
            if cancel.is_set():
                _kill_process(proc)
                return
            time.sleep(0.2)

    def _finish(
        self,
        store: JobStore,
        job: Job,
        status: str,
        result: str = "",
        error: str = "",
    ) -> None:
        text = "Finished" if status == "done" else ("Canceled" if status == "canceled" else error or "Failed")

        def apply(j: Job) -> None:
            j.status = status
            j.finished_at = time.time()
            if result:
                j.result = result
            if error:
                j.error = error
            if j.started_at:
                j.duration_ms = int((j.finished_at - j.started_at) * 1000)
            # Append inside the same lock as the status change so SSE cannot
            # close on "done" before the phone receives the Finished event.
            payload = {"kind": "status", "text": text, "status": status, "ts": time.time()}
            j.events.append(payload)

        store.mutate(job.id, apply)
        finished = store.get(job.id)
        if finished:
            try:
                notify_job(finished)
            except Exception:  # noqa: BLE001 — never fail a job because the banner could not show
                pass


def _desktop_result(ax_text: str, summary: dict) -> str:
    parts = []
    reply = (ax_text or "").strip()
    if reply:
        parts.append("Cursor desktop response:\n" + reply[-4000:])
    fixed = str(summary.get("text") or "").strip()
    if fixed:
        parts.append(fixed)
    return "\n\n".join(parts) or "Cursor ran the prompt in the desktop app."


def _new_text(before: str, after: str) -> str:
    if not after:
        return ""
    if before and after.startswith(before):
        return after[len(before) :]
    return after


def _kill_process(proc: subprocess.Popen[str]) -> None:
    try:
        if os.name == "posix" and proc.pid:
            os.killpg(os.getpgid(proc.pid), 15)
        else:
            proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix" and proc.pid:
                os.killpg(os.getpgid(proc.pid), 9)
            else:
                proc.kill()
        except OSError:
            pass
