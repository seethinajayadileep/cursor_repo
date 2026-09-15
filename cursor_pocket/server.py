"""Stdlib HTTP + SSE server. Phone and laptop talk only over the local network."""

from __future__ import annotations

import json
import mimetypes
import posixpath
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import __app_name__, __version__
from .apk import apk_path
from .auth import Auth, AuthError, extract_bearer
from .jobs import JobStore
from .net import public_base_urls
from .runner import Runner

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
MODES = {"agent", "ask", "plan", "cloud"}


class PocketState:
    def __init__(
        self,
        *,
        auth: Auth,
        store: JobStore,
        runner: Runner,
        workspaces: list[dict[str, str]],
        host: str,
        port: int,
        laptop_name: str,
    ) -> None:
        self.auth = auth
        self.store = store
        self.runner = runner
        self.workspaces = workspaces
        self.host = host
        self.port = port
        self.laptop_name = laptop_name
        self.online_url: str | None = None


class PocketHandler(BaseHTTPRequestHandler):
    server_version = "CursorPocket/0.1"

    @property
    def state(self) -> PocketState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        msg = fmt % args
        if "/events" in msg:
            return
        writer = getattr(self.server, "log", print)
        if callable(writer):
            writer(f"{self.address_string()} {msg}")

    def _is_loopback(self) -> bool:
        # Cloudflare / ngrok proxy through 127.0.0.1 — treat forwarded requests as remote
        # so the pairing PIN never leaks on a public URL.
        for header in ("X-Forwarded-For", "CF-Connecting-IP", "X-Real-IP", "Forwarded"):
            if self.headers.get(header):
                return False
        addr = self.client_address[0]
        return addr in {"127.0.0.1", "::1", "::ffff:127.0.0.1"}

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/health":
                self._json(200, self._health())
                return
            if path in {"/apk", "/apk/", "/apk/cursor-pocket.apk", "/cursor-pocket.apk"}:
                self._apk()
                return
            if path == "/api/host":
                self._host_info()
                return
            if path == "/api/status":
                self._require(query)
                self._json(200, self._status())
                return
            if path == "/api/jobs":
                self._require(query)
                jobs = [job.snapshot() for job in self.state.store.list()]
                self._json(200, {"jobs": jobs})
                return
            if path.startswith("/api/jobs/") and path.endswith("/events"):
                self._require(query)
                job_id = path[len("/api/jobs/") : -len("/events")]
                self._sse(job_id, query)
                return
            if path.startswith("/api/jobs/"):
                self._require(query)
                job_id = path.split("/")[-1]
                job = self.state.store.get(job_id)
                if not job:
                    self._json(404, {"error": "No job with that id"})
                    return
                self._json(200, {"job": job.snapshot(include_events=True)})
                return
            self._static(path)
        except AuthError as exc:
            self._json(exc.status, {"error": str(exc)})
        except BrokenPipeError:
            return

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            body = self._read_json()
            if path == "/api/pair":
                token = self.state.auth.pair(str(body.get("pin") or ""))
                self._json(200, {"token": token, "laptop": self.state.laptop_name})
                return
            if path == "/api/unpair":
                self._require(query)
                token = extract_bearer(self.headers.get("Authorization"), (query.get("token") or [None])[0])
                if token:
                    self.state.auth.revoke(token)
                self._json(200, {"ok": True})
                return
            if path == "/api/jobs":
                self._require(query)
                job = self._create_job(body)
                self._json(201, {"job": job.snapshot()})
                return
            if path.startswith("/api/jobs/") and path.endswith("/cancel"):
                self._require(query)
                job_id = path[len("/api/jobs/") : -len("/cancel")]
                ok = self.state.store.request_cancel(job_id)
                if not ok:
                    self._json(404, {"error": "Nothing to cancel"})
                    return
                job = self.state.store.get(job_id)
                self._json(200, {"job": job.snapshot() if job else None})
                return
            if path.startswith("/api/jobs/") and path.endswith("/follow-up"):
                self._require(query)
                job_id = path[len("/api/jobs/") : -len("/follow-up")]
                job = self._follow_up(job_id, body)
                self._json(201, {"job": job.snapshot()})
                return
            self._json(404, {"error": "Unknown endpoint"})
        except AuthError as exc:
            self._json(exc.status, {"error": str(exc)})
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
        except BrokenPipeError:
            return

    def _require(self, query: dict[str, list[str]]) -> None:
        token = extract_bearer(self.headers.get("Authorization"), (query.get("token") or [None])[0])
        self.state.auth.check(token)

    def _health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "app": "cursor-pocket",
            "name": __app_name__,
            "version": __version__,
            "laptop": self.state.laptop_name,
            "agent": self.state.runner.available(),
            "demo": self.state.runner.demo,
            "online": bool(self.state.online_url),
            "target": self.state.runner.target,
            "apk": apk_path() is not None,
        }

    def _host_info(self) -> None:
        if not self._is_loopback():
            self._json(403, {"error": "Open /host on the laptop itself to see the PIN."})
            return
        self._json(
            200,
            {
                "pin": self.state.auth.pin,
                "laptop": self.state.laptop_name,
                "urls": public_base_urls(self.state.host, self.state.port),
                "workspaces": self.state.workspaces,
                "demo": self.state.runner.demo,
                "agent_path": self.state.runner.agent_bin,
                "version": __version__,
                "online_url": self.state.online_url,
                "target": self.state.runner.target,
                "apk": apk_path() is not None,
            },
        )

    def _status(self) -> dict[str, Any]:
        return {
            "laptop": self.state.laptop_name,
            "agent_path": self.state.runner.agent_bin,
            "demo": self.state.runner.demo,
            "agent_available": self.state.runner.available(),
            "target": self.state.runner.target,
            "workspaces": self.state.workspaces,
            "jobs": [job.snapshot() for job in self.state.store.list()[:30]],
        }

    def _create_job(self, body: dict[str, Any], *, follow_up_of: str | None = None, session_id: str | None = None) -> Any:
        prompt = str(body.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("Type a prompt first")
        mode = str(body.get("mode") or "agent").strip().lower()
        if mode not in MODES:
            raise ValueError("Mode must be agent, ask, or plan")
        workspace = self._pick_workspace(body.get("workspace"))
        model = str(body.get("model") or "").strip() or None
        job = self.state.store.create(
            prompt=prompt,
            workspace=workspace["path"],
            workspace_name=workspace["name"],
            mode=mode,
            follow_up_of=follow_up_of,
            session_id=session_id,
            model=model,
        )
        self.state.runner.start(self.state.store, job)
        return job

    def _follow_up(self, job_id: str, body: dict[str, Any]) -> Any:
        parent = self.state.store.get(job_id)
        if not parent:
            raise ValueError("Original job not found")
        if not parent.session_id:
            raise ValueError("That run has no session to resume")
        body = dict(body)
        body.setdefault("workspace", parent.workspace)
        body.setdefault("mode", parent.mode)
        return self._create_job(body, follow_up_of=parent.id, session_id=parent.session_id)

    def _pick_workspace(self, requested: Any) -> dict[str, str]:
        if not self.state.workspaces:
            raise ValueError("No workspace configured on the laptop")
        if not requested:
            return self.state.workspaces[0]
        key = str(requested)
        for item in self.state.workspaces:
            if item["path"] == key or item["name"] == key:
                return item
        raise ValueError("Unknown workspace")

    def _sse(self, job_id: str, query: dict[str, list[str]]) -> None:
        job = self.state.store.get(job_id)
        if not job:
            self._json(404, {"error": "No job with that id"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()
        self.close_connection = True
        cursor = len(job.events)
        try:
            after = (query.get("after") or [None])[0]
            if after not in {None, ""}:
                cursor = int(after)
        except ValueError:
            cursor = len(job.events)
        try:
            snapshot = json.dumps({"kind": "snapshot", "job": job.snapshot(include_events=True)})
            self.wfile.write(f"data: {snapshot}\n\n".encode())
            self.wfile.flush()
            while True:
                job, events = self.state.store.wait_events(job_id, cursor, timeout=12.0)
                if job is None:
                    self.wfile.write(b"event: gone\ndata: {}\n\n")
                    self.wfile.flush()
                    return
                for event in events:
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                    cursor += 1
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                if job.status in {"done", "error", "canceled"} and not events:
                    self.wfile.write(
                        f"data: {json.dumps({'kind': 'end', 'job': job.snapshot()})}\n\n".encode()
                    )
                    self.wfile.flush()
                    return
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return

    def _apk(self) -> None:
        path = apk_path()
        if not path:
            self._json(404, {"error": "No APK on this laptop yet. Build android/ or download the GitHub Action artifact."})
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.android.package-archive")
        self.send_header("Content-Disposition", 'attachment; filename="cursor-pocket.apk"')
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str) -> None:
        if path in {"/host", "/host/"}:
            path = "/host.html"
        relative = path if path != "/" else "/index.html"
        relative = posixpath.normpath(relative).lstrip("/")
        target = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in target.parents and target != WEB_ROOT.resolve():
            self._json(403, {"error": "Nope"})
            return
        if not target.is_file():
            # SPA-style fallback keeps phone deep links working.
            target = WEB_ROOT / "index.html"
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix == ".webmanifest":
            ctype = "application/manifest+json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length > 1_000_000:
            raise ValueError("Prompt is too large")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Body must be JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("Body must be a JSON object")
        return data

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _cors(self) -> None:
        # Same-LAN PWA. Credentials stay token-based, not cookie-based.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


class PocketHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr: tuple[str, int], state: PocketState) -> None:
        self.state = state
        self.log = print
        super().__init__(addr, PocketHandler)


def serve(state: PocketState, host: str, port: int) -> PocketHTTPServer:
    httpd = PocketHTTPServer((host, port), state)
    actual_port = httpd.server_address[1]
    state.port = actual_port
    thread = threading.Thread(target=partial(httpd.serve_forever, poll_interval=0.2), daemon=True)
    thread.start()
    httpd.thread = thread  # type: ignore[attr-defined]
    return httpd
