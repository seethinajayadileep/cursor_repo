"""Git change summaries for the phone."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from cursor_pocket.changes import describe_changes, snapshot
from cursor_pocket.runner import _new_text


class ChangesTests(unittest.TestCase):
    def test_reports_edited_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._git(root, ["init"])
            self._git(root, ["config", "user.email", "pocket@test"])
            self._git(root, ["config", "user.name", "Pocket"])
            (root / "a.txt").write_text("one\n", encoding="utf-8")
            self._git(root, ["add", "a.txt"])
            self._git(root, ["commit", "-m", "init"])
            before = snapshot(str(root))
            (root / "a.txt").write_text("fixed\n", encoding="utf-8")
            info = describe_changes(str(root), before)
            self.assertIn("a.txt", info["files"])
            self.assertIn("fixed", str(info["text"]))

    def test_no_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._git(root, ["init"])
            self._git(root, ["config", "user.email", "pocket@test"])
            self._git(root, ["config", "user.name", "Pocket"])
            (root / "a.txt").write_text("one\n", encoding="utf-8")
            self._git(root, ["add", "a.txt"])
            self._git(root, ["commit", "-m", "init"])
            before = snapshot(str(root))
            info = describe_changes(str(root), before)
            self.assertEqual(info["files"], [])
            self.assertIn("did not change", str(info["text"]))

    def _git(self, root: Path, args: list[str]) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class DesktopTextTests(unittest.TestCase):
    def test_new_text_suffix(self) -> None:
        self.assertEqual(_new_text("hello", "hello world"), " world")
        self.assertEqual(_new_text("", "abc"), "abc")


if __name__ == "__main__":
    unittest.main()
