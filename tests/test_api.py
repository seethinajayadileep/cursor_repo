"""HTTP API: pair, run demo job, stream, cancel."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import unittest

from cursor_pocket.auth import Auth
from cursor_pocket.jobs import JobStore
from cursor_pocket.runner import Runner
from cursor_pocket.server import PocketState, serve


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth = Auth.generate("123456")
        self.state = PocketState(
            auth=self.auth,
            store=JobStore(),
            runner=Runner(demo=True),
            workspaces=[{"name": "workspace", "path": "/tmp"}],
            host="127.0.0.1",
            port=0,
            laptop_name="test-laptop",
        )
        self.httpd = serve(self.state, "127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def _json(self, method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode())
            return exc.code, payload

    def test_health_and_phone_home(self) -> None:
        status, body = self._json("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        req = urllib.request.Request(self.base + "/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode()
        self.assertIn("Cursor Pocket", html)
        self.assertIn("Pair with laptop", html)
        self.assertIn("apk", body)
        self.assertIn("Install Android app", html)

    def test_host_includes_online_url(self) -> None:
        self.state.online_url = "https://demo.trycloudflare.com"
        status, body = self._json("GET", "/api/host")
        self.assertEqual(status, 200)
        self.assertEqual(body["online_url"], "https://demo.trycloudflare.com")
        status, health = self._json("GET", "/api/health")
        self.assertTrue(health["online"])

    def test_host_pin_on_localhost(self) -> None:
        status, body = self._json("GET", "/api/host")
        self.assertEqual(status, 200)
        self.assertEqual(body["pin"], "123456")
        self.assertIsNone(body.get("online_url"))

    def test_host_pin_hidden_when_forwarded(self) -> None:
        req = urllib.request.Request(
            self.base + "/api/host",
            headers={"X-Forwarded-For": "203.0.113.8"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = json.loads(exc.read().decode())
        self.assertEqual(status, 403)
        self.assertNotIn("pin", body)

    def test_pair_rejects_wrong_pin(self) -> None:
        status, body = self._json("POST", "/api/pair", {"pin": "000000"})
        self.assertEqual(status, 401)
        self.assertIn("Wrong PIN", body["error"])

    def test_demo_job_completes(self) -> None:
        status, paired = self._json("POST", "/api/pair", {"pin": "123456"})
        self.assertEqual(status, 200)
        token = paired["token"]
        status, created = self._json("POST", "/api/jobs", {"prompt": "fix the tests"}, token=token)
        self.assertEqual(status, 201)
        job_id = created["job"]["id"]
        deadline = time.time() + 8
        job = created["job"]
        while time.time() < deadline:
            status, payload = self._json("GET", f"/api/jobs/{job_id}", token=token)
            self.assertEqual(status, 200)
            job = payload["job"]
            if job["status"] in {"done", "error", "canceled"}:
                break
            time.sleep(0.15)
        self.assertEqual(job["status"], "done")
        self.assertTrue(job["session_id"])
        events = job["events"]
        kinds = [event.get("kind") for event in events]
        self.assertIn("assistant", kinds)
        self.assertIn("changes", kinds)
        self.assertIn("result", kinds)
        self.assertEqual(events[-1]["kind"], "status")
        self.assertEqual(events[-1]["text"], "Finished")
        assistant = "\n".join(event["text"] for event in events if event.get("kind") == "assistant")
        self.assertIn("Cursor desktop would answer here", assistant)
        changes = next(event["text"] for event in events if event.get("kind") == "changes")
        self.assertIn("What was fixed", changes)
        status, follow = self._json(
            "POST", f"/api/jobs/{job_id}/follow-up", {"prompt": "also run the linter"}, token=token
        )
        self.assertEqual(status, 201)
        self.assertEqual(follow["job"]["follow_up_of"], job_id)
        status, listing = self._json("GET", "/api/jobs", token=token)
        self.assertEqual(status, 200)
        ids = [item["id"] for item in listing["jobs"]]
        self.assertIn(job_id, ids)
        self.assertIn(follow["job"]["id"], ids)

    def test_cancel_unknown_job(self) -> None:
        status, paired = self._json("POST", "/api/pair", {"pin": "123456"})
        token = paired["token"]
        status, body = self._json("POST", "/api/jobs/missing/cancel", {}, token=token)
        self.assertEqual(status, 404)
        self.assertIn("cancel", body["error"].lower())

    def test_jobs_require_auth(self) -> None:
        status, body = self._json("GET", "/api/jobs")
        self.assertEqual(status, 401)
        self.assertIn("Pair", body["error"])


if __name__ == "__main__":
    unittest.main()
