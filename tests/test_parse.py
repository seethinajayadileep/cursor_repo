"""Cursor CLI stream-json → phone events."""

from __future__ import annotations

import unittest

from cursor_pocket.parse import parse_stream_line, summarize_event


class ParseTests(unittest.TestCase):
    def test_plain_log_line(self) -> None:
        event = parse_stream_line("not json")
        self.assertEqual(event["kind"], "log")

    def test_system_init(self) -> None:
        event = summarize_event(
            {"type": "system", "subtype": "init", "model": "demo", "cwd": "/proj", "session_id": "s1"}
        )
        self.assertEqual(event["kind"], "system")
        self.assertEqual(event["session_id"], "s1")
        self.assertIn("demo", event["text"])

    def test_assistant_text(self) -> None:
        event = summarize_event(
            {
                "type": "assistant",
                "timestamp_ms": 1,
                "message": {"content": [{"type": "text", "text": "Hello"}]},
            }
        )
        self.assertEqual(event["kind"], "assistant")
        self.assertEqual(event["text"], "Hello")
        self.assertTrue(event["delta"])

    def test_tool_read(self) -> None:
        event = summarize_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {"readToolCall": {"args": {"path": "README.md"}}},
            }
        )
        self.assertEqual(event["kind"], "tool")
        self.assertIn("README.md", event["text"])

    def test_result(self) -> None:
        event = summarize_event(
            {"type": "result", "result": "all good", "is_error": False, "session_id": "s2", "duration_ms": 9}
        )
        self.assertEqual(event["kind"], "result")
        self.assertEqual(event["session_id"], "s2")
        self.assertFalse(event["error"])

    def test_user_ignored(self) -> None:
        self.assertIsNone(summarize_event({"type": "user"}))

    def test_thinking_event(self) -> None:
        event = summarize_event(
            {"type": "thinking", "text": "Planning next moves", "duration_ms": 5000}
        )
        self.assertEqual(event["kind"], "thinking")
        self.assertEqual(event["text"], "Planning next moves")
        self.assertEqual(event["duration_ms"], 5000)

    def test_assistant_thinking_blocks(self) -> None:
        event = summarize_event(
            {
                "type": "assistant",
                "timestamp_ms": 2,
                "message": {
                    "content": [{"type": "thinking", "thinking": "I'll inspect the files first."}]
                },
            }
        )
        self.assertEqual(event["kind"], "thinking")
        self.assertIn("inspect", event["text"])


if __name__ == "__main__":
    unittest.main()
