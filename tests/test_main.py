"""CLI flags: --demo is ignored when Cursor desktop is installed."""

from __future__ import annotations

import unittest

from cursor_pocket.__main__ import _parse, resolve_demo
from cursor_pocket.desktop import parse_chat_names, resolve_cloud_target


class ResolveDemoTests(unittest.TestCase):
    def test_no_flags_is_live(self) -> None:
        demo, note = resolve_demo(False, fake=False, cursor_installed=True)
        self.assertFalse(demo)
        self.assertEqual(note, "")

    def test_demo_ignored_when_cursor_installed(self) -> None:
        demo, note = resolve_demo(True, fake=False, cursor_installed=True)
        self.assertFalse(demo)
        self.assertIn("--fake", note)
        self.assertIn("live", note)

    def test_demo_stays_when_cursor_missing(self) -> None:
        demo, note = resolve_demo(True, fake=False, cursor_installed=False)
        self.assertTrue(demo)
        self.assertEqual(note, "")

    def test_fake_always_demos(self) -> None:
        demo, note = resolve_demo(True, fake=True, cursor_installed=True)
        self.assertTrue(demo)
        self.assertEqual(note, "")
        demo, note = resolve_demo(False, fake=True, cursor_installed=True)
        self.assertTrue(demo)

    def test_parse_fake_and_demo(self) -> None:
        args = _parse(["--demo", "--pin", "123456"])
        self.assertTrue(args.demo)
        self.assertFalse(args.fake)
        args = _parse(["--fake", "--pin", "123456"])
        self.assertTrue(args.fake)


class CloudChatPickTests(unittest.TestCase):
    def test_parse_chat_names_drops_chrome(self) -> None:
        raw = "\n".join(
            [
                "New Chat",
                "Search",
                "Mobile offline Cursor control",
                "Cloud",
                "Open source testing",
                "IDE",
            ]
        )
        names = parse_chat_names(raw)
        self.assertEqual(names, ["Mobile offline Cursor control", "Open source testing"])

    def test_resolve_cloud_target(self) -> None:
        self.assertEqual(resolve_cloud_target(""), "current")
        self.assertEqual(resolve_cloud_target("new"), "new")
        self.assertEqual(resolve_cloud_target("Mobile offline Cursor control"), "Mobile offline Cursor control")
        self.assertEqual(resolve_cloud_target("new", follow_up=True), "current")
