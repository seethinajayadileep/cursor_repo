"""End-to-end: phone HTTP API → mocked Cursor desktop → reply + file fixes.

This Linux CI environment cannot launch Cursor.app or osascript. The desktop
driver is replaced with a fake that grows Accessibility text and edits a git
repo the same way a real Cursor session would, then the real HTTP server,
job runner, and change summary are exercised.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from cursor_pocket.auth import Auth
from cursor_pocket.desktop import DesktopError, cloud_script, desktop_available, send_prompt
from cursor_pocket.jobs import JobStore
from cursor_pocket.runner import Runner, _desktop_result
from cursor_pocket.server import PocketState, serve


def _git(root: Path, args: list[str]) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    _git(root, ["init"])
    _git(root, ["config", "user.email", "pocket@test"])
    _git(root, ["config", "user.name", "Pocket"])
    (root / "a.txt").write_text("broken\n", encoding="utf-8")
    _git(root, ["add", "a.txt"])
    _git(root, ["commit", "-m", "init"])


class FakeCursorDesktop:
    """Stand-in for Accessibility + pbcopy + osascript on a Mac."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.opened: list[str] = []
        self.copied: list[str] = []
        self.send_count = 0
        self.sends: list[dict] = []
        self.stop_count = 0
        self.reads = 0
        self.silent = False
        self._baseline = "Chat\nComposer\n"

    def open_workspace(self, path: str) -> None:
        self.opened.append(path)

    def copy_prompt(self, prompt: str) -> None:
        self.copied.append(prompt)

    def send_prompt(self, *args, **kwargs) -> None:
        self.send_count += 1
        self.sends.append({"args": args, "kwargs": kwargs})
        self.reads = 0

    def request_stop(self) -> None:
        self.stop_count += 1

    def read_cursor_text(self) -> str:
        self.reads += 1
        if self.silent or self.reads <= 1:
            return self._baseline
        if self.reads == 2:
            if self.send_count <= 1:
                (self.workspace / "a.txt").write_text("hello from pocket\n", encoding="utf-8")
            else:
                (self.workspace / "b.txt").write_text("follow-up fix\n", encoding="utf-8")
        return (
            self._baseline
            + "I'll update a.txt so the tests pass.\n"
            + "Done. Changed a.txt.\n"
        )


class DesktopE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_repo(self.root)
        self.fake = FakeCursorDesktop(self.root)
        self.auth = Auth.generate("123456")
        self.runner = Runner(
            demo=False,
            target="desktop",
            idle_seconds=0.0,
            poll_seconds=0.02,
            open_delay=0.0,
            after_send_delay=0.0,
            no_activity_seconds=0.25,
            max_seconds=8.0,
        )
        self.state = PocketState(
            auth=self.auth,
            store=JobStore(),
            runner=self.runner,
            workspaces=[{"name": self.root.name, "path": str(self.root)}],
            host="127.0.0.1",
            port=0,
            laptop_name="e2e-laptop",
        )
        self._patches = [
            patch("cursor_pocket.runner.desktop_available", return_value=True),
            patch("cursor_pocket.runner.open_workspace", self.fake.open_workspace),
            patch("cursor_pocket.runner.copy_prompt", self.fake.copy_prompt),
            patch("cursor_pocket.runner.send_prompt", self.fake.send_prompt),
            patch("cursor_pocket.runner.read_cursor_text", self.fake.read_cursor_text),
            patch("cursor_pocket.runner.request_stop", self.fake.request_stop),
        ]
        for item in self._patches:
            item.start()
        self.httpd = serve(self.state, "127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        for item in reversed(self._patches):
            item.stop()
        self._tmp.cleanup()

    def _json(self, method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode())
            return exc.code, payload

    def _pair(self) -> str:
        status, paired = self._json("POST", "/api/pair", {"pin": "123456"})
        self.assertEqual(status, 200)
        return paired["token"]

    def _wait_job(self, job_id: str, token: str, timeout: float = 6.0) -> dict:
        deadline = time.time() + timeout
        job: dict = {}
        while time.time() < deadline:
            status, payload = self._json("GET", f"/api/jobs/{job_id}", token=token)
            self.assertEqual(status, 200)
            job = payload["job"]
            if job["status"] in {"done", "error", "canceled"}:
                return job
            time.sleep(0.04)
        self.fail(f"job {job_id} did not finish: {job}")

    def _read_sse(self, job_id: str, token: str, timeout: float = 6.0) -> list[dict]:
        req = urllib.request.Request(
            f"{self.base}/api/jobs/{job_id}/events?token={token}",
            headers={"Accept": "text/event-stream", "Connection": "close"},
        )
        events: list[dict] = []
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            buf = ""
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    chunk = resp.read(1)
                except TimeoutError:
                    break
                if not chunk:
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n\n" in buf:
                    block, buf = buf.split("\n\n", 1)
                    for line in block.splitlines():
                        if line.startswith("data: "):
                            events.append(json.loads(line[6:]))
                    if any(item.get("kind") == "end" for item in events):
                        return events
        return events

    def test_health_reports_desktop_target(self) -> None:
        status, body = self._json("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["target"], "desktop")
        self.assertTrue(body["agent"])
        self.assertFalse(body["demo"])

    def test_prompt_is_sent_and_phone_gets_reply_and_fix(self) -> None:
        token = self._pair()
        status, created = self._json(
            "POST",
            "/api/jobs",
            {"prompt": "fix a.txt so the tests pass"},
            token=token,
        )
        self.assertEqual(status, 201)
        job_id = created["job"]["id"]

        sse_events: list[dict] = []
        errors: list[BaseException] = []

        def _sse() -> None:
            try:
                sse_events.extend(self._read_sse(job_id, token))
            except BaseException as exc:  # noqa: BLE001 — surface thread failure in the assertion
                errors.append(exc)

        watcher = threading.Thread(target=_sse, daemon=True)
        watcher.start()
        job = self._wait_job(job_id, token)
        watcher.join(timeout=4)
        self.assertFalse(errors, errors)

        self.assertEqual(job["status"], "done")
        self.assertEqual(self.fake.send_count, 1)
        self.assertEqual(self.fake.sends[0]["kwargs"].get("kind"), "agent")
        self.assertEqual(self.fake.copied, ["fix a.txt so the tests pass"])
        self.assertEqual(self.fake.opened, [str(self.root)])
        self.assertTrue(job["session_id"].startswith("desktop-"))
        self.assertIn("I'll update a.txt", job["result"])
        self.assertIn("a.txt", job["result"])
        self.assertIn("hello from pocket", job["result"])

        kinds = [event.get("kind") for event in job["events"]]
        self.assertIn("assistant", kinds)
        self.assertIn("changes", kinds)
        self.assertIn("result", kinds)
        self.assertEqual(kinds[-1], "status")
        self.assertEqual(job["events"][-1]["text"], "Finished")

        assistant = next(event["text"] for event in job["events"] if event.get("kind") == "assistant")
        self.assertIn("I'll update a.txt", assistant)
        changes = next(event["text"] for event in job["events"] if event.get("kind") == "changes")
        self.assertIn("a.txt", changes)

        self.assertTrue(sse_events)
        streamed: list[dict] = []
        for event in sse_events:
            if event.get("kind") == "snapshot":
                streamed.extend(event.get("job", {}).get("events") or [])
            else:
                streamed.append(event)
        sse_kinds = [event.get("kind") for event in streamed]
        self.assertIn("end", [event.get("kind") for event in sse_events])
        self.assertIn("assistant", sse_kinds)
        self.assertIn("changes", sse_kinds)
        end = next(event for event in sse_events if event.get("kind") == "end")
        self.assertEqual(end["job"]["status"], "done")

        status, follow = self._json(
            "POST",
            f"/api/jobs/{job_id}/follow-up",
            {"prompt": "also add b.txt"},
            token=token,
        )
        self.assertEqual(status, 201)
        follow_job = self._wait_job(follow["job"]["id"], token)
        self.assertEqual(follow_job["status"], "done")
        self.assertEqual(follow_job["follow_up_of"], job_id)
        self.assertEqual(self.fake.send_count, 2)
        self.assertIn("b.txt", follow_job["result"])
        self.assertTrue((self.root / "b.txt").exists())

    def test_cancel_stops_desktop_before_idle_finish(self) -> None:
        self.fake.silent = True
        self.runner.idle_seconds = 30.0
        self.runner.no_activity_seconds = 30.0
        token = self._pair()
        status, created = self._json("POST", "/api/jobs", {"prompt": "hang please"}, token=token)
        self.assertEqual(status, 201)
        job_id = created["job"]["id"]
        deadline = time.time() + 3
        while time.time() < deadline:
            _, payload = self._json("GET", f"/api/jobs/{job_id}", token=token)
            if payload["job"]["status"] == "running" and self.fake.send_count:
                break
            time.sleep(0.03)
        status, canceled = self._json("POST", f"/api/jobs/{job_id}/cancel", {}, token=token)
        self.assertEqual(status, 200)
        job = self._wait_job(job_id, token)
        self.assertEqual(job["status"], "canceled")
        self.assertGreaterEqual(self.fake.stop_count, 1)

    def test_no_activity_still_returns_a_result(self) -> None:
        self.fake.silent = True
        token = self._pair()
        status, created = self._json("POST", "/api/jobs", {"prompt": "nothing happens"}, token=token)
        self.assertEqual(status, 201)
        job = self._wait_job(created["job"]["id"], token)
        self.assertEqual(job["status"], "done")
        self.assertIn("could not be read", job["result"])
        assistant = next(event["text"] for event in job["events"] if event.get("kind") == "assistant")
        self.assertIn("Accessibility", assistant)

    def test_cloud_mode_opens_agents_composer(self):
        token = self._pair()
        status, created = self._json(
            "POST",
            "/api/jobs",
            {"prompt": "run this in cloud agents", "mode": "cloud"},
            token=token,
        )
        self.assertEqual(status, 201)
        job = self._wait_job(created["job"]["id"], token)
        self.assertEqual(job["status"], "done")
        self.assertTrue(job["session_id"].startswith("cloud-"))
        self.assertEqual(self.fake.opened, [])
        self.assertEqual(self.fake.sends[0]["kwargs"]["kind"], "cloud")
        from cursor_pocket.notify import LAST as notice
        self.assertEqual(notice[0], "Cloud Agent finished")
        self.assertFalse(self.fake.sends[0]["kwargs"]["new_chat"])
        self.assertEqual(self.fake.sends[0]["kwargs"].get("chat"), "current")
        status, follow = self._json(
            "POST",
            f"/api/jobs/{job['id']}/follow-up",
            {"prompt": "continue"},
            token=token,
        )
        self.assertEqual(status, 201)
        follow_job = self._wait_job(follow["job"]["id"], token)
        self.assertEqual(follow_job["status"], "done")
        self.assertEqual(self.fake.sends[-1]["kwargs"]["kind"], "cloud")
        self.assertFalse(self.fake.sends[-1]["kwargs"]["new_chat"])

    def test_cloud_mode_named_chat_and_new_chat(self):
        token = self._pair()
        status, created = self._json(
            "POST",
            "/api/jobs",
            {"prompt": "continue this thread", "mode": "cloud", "chat": "Mobile offline Cursor control"},
            token=token,
        )
        self.assertEqual(status, 201)
        job = self._wait_job(created["job"]["id"], token)
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["chat"], "Mobile offline Cursor control")
        self.assertEqual(self.fake.sends[0]["kwargs"]["chat"], "Mobile offline Cursor control")
        self.assertFalse(self.fake.sends[0]["kwargs"]["new_chat"])
        status, created = self._json(
            "POST",
            "/api/jobs",
            {"prompt": "start over", "mode": "cloud", "chat": "new"},
            token=token,
        )
        self.assertEqual(status, 201)
        job = self._wait_job(created["job"]["id"], token)
        self.assertEqual(job["status"], "done")
        self.assertTrue(self.fake.sends[-1]["kwargs"]["new_chat"])
        self.assertEqual(self.fake.sends[-1]["kwargs"]["chat"], "new")


class DesktopGuardsTests(unittest.TestCase):
    def test_desktop_unavailable_on_linux(self) -> None:
        self.assertFalse(desktop_available())

    def test_send_prompt_refuses_non_mac(self) -> None:
        with self.assertRaises(DesktopError):
            send_prompt()

    def test_cloud_script_opens_agents_window_not_ide(self) -> None:
        script = cloud_script(new_chat=True)
        self.assertIn("New Agents Window", script)
        self.assertIn("New Chat", script)
        self.assertIn("Cloud", script)
        self.assertNotIn('keystroke "i" using {command down}', script)
        current = cloud_script(chat="current")
        self.assertNotIn("New Chat", current)
        named = cloud_script(chat="Mobile offline Cursor control")
        self.assertIn("Mobile offline Cursor control", named)
        self.assertNotIn("New Chat", named)

    def test_desktop_result_joins_reply_and_files(self) -> None:
        text = _desktop_result("hello from Cursor", {"text": "Files Cursor changed:\n  • a.txt"})
        self.assertIn("Cursor desktop response", text)
        self.assertIn("hello from Cursor", text)
        self.assertIn("a.txt", text)


if __name__ == "__main__":
    unittest.main()
