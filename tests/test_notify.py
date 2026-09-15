"""Laptop notifications when a Pocket job ends."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cursor_pocket.notify import notice_for, notify_job, _escape


class NoticeTests(unittest.TestCase):
    def test_cloud_done(self) -> None:
        title, body = notice_for(SimpleNamespace(status="done", mode="cloud", prompt="fix tests", error=""))
        self.assertEqual(title, "Cloud Agent finished")
        self.assertEqual(body, "fix tests")

    def test_agent_done(self) -> None:
        title, body = notice_for(SimpleNamespace(status="done", mode="agent", prompt="hello", error=""))
        self.assertEqual(title, "Cursor finished")

    def test_failed_uses_error_if_no_prompt(self) -> None:
        title, body = notice_for(SimpleNamespace(status="error", mode="agent", prompt="", error="Accessibility denied"))
        self.assertEqual(title, "Cursor failed")
        self.assertEqual(body, "Accessibility denied")

    def test_canceled(self) -> None:
        title, _body = notice_for(SimpleNamespace(status="canceled", mode="cloud", prompt="x", error=""))
        self.assertEqual(title, "Cursor canceled")

    def test_escape_quotes(self) -> None:
        self.assertEqual(_escape('say "hi"'), r"say \"hi\"")

    def test_notify_job_records_last(self) -> None:
        job = SimpleNamespace(status="done", mode="cloud", prompt="open agents", error="")
        with patch("cursor_pocket.notify._mac") as mac:
            notify_job(job)
        from cursor_pocket import notify
        self.assertEqual(notify.LAST, ("Cloud Agent finished", "open agents"))
        mac.assert_called_once()
