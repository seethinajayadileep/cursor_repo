"""Drive the Cursor desktop app on macOS: paste the prompt, press Send, read the window."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CURSOR_APP = Path("/Applications/Cursor.app")

SEND_SCRIPT = r"""
tell application "Cursor" to activate
delay 1.0
tell application "System Events"
  if not (exists process "Cursor") then error "Cursor desktop is not running."
  tell process "Cursor" to set frontmost to true
  delay 0.4
  keystroke "i" using {command down}
  delay 0.7
  keystroke "v" using {command down}
  delay 0.4
  key code 36
end tell
"""

READ_SCRIPT = r"""
tell application "System Events"
  if not (exists process "Cursor") then return ""
  tell process "Cursor"
    set chunks to {}
    try
      set chunks to value of every static text of window 1
    end try
    set out to ""
    repeat with t in chunks
      set out to out & (t as text) & linefeed
    end repeat
    return out
  end tell
end tell
"""

STOP_SCRIPT = r"""
tell application "Cursor" to activate
delay 0.2
tell application "System Events"
  key code 53
end tell
"""


class DesktopError(RuntimeError):
    pass


def desktop_available() -> bool:
    if sys.platform != "darwin":
        return False
    return CURSOR_APP.exists() or bool(shutil.which("cursor"))


def open_workspace(workspace: str) -> None:
    cursor_bin = shutil.which("cursor")
    if cursor_bin:
        subprocess.Popen([cursor_bin, workspace], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603
        return
    if CURSOR_APP.exists():
        subprocess.Popen(  # noqa: S603
            ["open", "-a", "Cursor", workspace],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    raise DesktopError("Cursor desktop app was not found. Install Cursor, then open your project in it.")


def copy_prompt(prompt: str) -> None:
    subprocess.run(["pbcopy"], input=prompt.encode("utf-8"), check=True, timeout=10)


def send_prompt() -> None:
    _osascript(SEND_SCRIPT)


def read_cursor_text() -> str:
    try:
        return _osascript(READ_SCRIPT).strip()
    except DesktopError:
        return ""


def request_stop() -> None:
    try:
        _osascript(STOP_SCRIPT)
    except DesktopError:
        return


def _osascript(script: str) -> str:
    if sys.platform != "darwin":
        raise DesktopError("Cursor desktop automation only runs on a Mac.")
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        proc = subprocess.run(
            ["osascript", path],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "osascript failed").strip()
        if "not allowed" in err.lower() or "1002" in err or "-1719" in err or "-1743" in err:
            raise DesktopError(
                "macOS blocked automation. System Settings → Privacy & Security → Accessibility: "
                "enable Terminal (or Python) and Cursor."
            )
        raise DesktopError(err)
    return proc.stdout or ""
