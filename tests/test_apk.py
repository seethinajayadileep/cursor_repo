"""APK discovery and download from the laptop daemon."""

from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from cursor_pocket.apk import apk_path
from cursor_pocket.auth import Auth
from cursor_pocket.jobs import JobStore
from cursor_pocket.runner import Runner
from cursor_pocket.server import PocketState, serve


class ApkPathTests(unittest.TestCase):
    def test_prefers_dist(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            dist = root / "android" / "dist"
            dist.mkdir(parents=True)
            apk = dist / "cursor-pocket.apk"
            apk.write_bytes(b"PK fake apk")
            self.assertEqual(apk_path(root), apk)

    def test_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            self.assertIsNone(apk_path(Path(raw)))


class ApkDownloadTests(unittest.TestCase):
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
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_missing_apk_is_404(self) -> None:
        with patch("cursor_pocket.server.apk_path", return_value=None):
            req = urllib.request.Request(self.base + "/apk/cursor-pocket.apk")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 404)

    def test_health_reports_apk_flag(self) -> None:
        req = urllib.request.Request(self.base + "/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        self.assertIn("apk", body)

    def test_serves_apk_bytes(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as handle:
            handle.write(b"PK\x03\x04pocket")
            path = Path(handle.name)
        try:
            with patch("cursor_pocket.server.apk_path", return_value=path):
                req = urllib.request.Request(self.base + "/apk/cursor-pocket.apk")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertEqual(resp.headers.get_content_type(), "application/vnd.android.package-archive")
                    self.assertEqual(resp.read(), b"PK\x03\x04pocket")
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
