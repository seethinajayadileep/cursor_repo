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

FOLLOW_SCRIPT = r"""
tell application "Cursor" to activate
delay 0.5
tell application "System Events"
  if not (exists process "Cursor") then error "Cursor desktop is not running."
  tell process "Cursor" to set frontmost to true
  delay 0.3
  try
    set areas to text areas of window 1
    if (count of areas) > 0 then
      click last item of areas
    end if
  end try
  delay 0.15
  keystroke "a" using {command down}
  delay 0.08
  keystroke "v" using {command down}
  delay 0.35
  key code 36
end tell
"""


def agent_script(*, new_chat: bool = True) -> str:
    """Cmd+I starts a desktop Agent. Follow-ups paste into the chat already open."""
    return SEND_SCRIPT if new_chat else FOLLOW_SCRIPT


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


def focus_cursor() -> None:
    """Bring Cursor to the front without opening a different project folder."""
    if sys.platform != "darwin":
        return
    subprocess.run(
        ["osascript", "-e", 'tell application "Cursor" to activate'],
        check=False,
        capture_output=True,
        timeout=10,
    )


CHAT_SKIP = frozenset(
    {
        "new chat",
        "search",
        "automations",
        "customize",
        "cloud",
        "agent",
        "high fast",
        "ide",
        "changes",
        "desktop",
        "browser",
        "terminal",
        "files",
        "cursor",
        "file",
        "edit",
        "view",
        "window",
        "help",
        "connect slack",
        "getting started",
        "plan",
        "build",
        "review",
        "listening",
        "install tonight",
        "remind me later",
        "updates available",
        "plus",
        "general chat",
    }
)


def parse_chat_names(raw: str) -> list[str]:
    """Turn Accessibility names into a de-duplicated chat list."""
    seen: set[str] = set()
    out: list[str] = []
    for line in (raw or "").splitlines():
        name = line.strip()
        key = name.lower()
        if not name or key in CHAT_SKIP or key in seen:
            continue
        if len(name) < 5 or len(name) > 80:
            continue
        if name.startswith("http") or name.startswith("/"):
            continue
        seen.add(key)
        out.append(name)
    return out[:40]


def resolve_cloud_target(chat: str, *, follow_up: bool = False) -> str:
    """new | current | a chat title from the Agents Window sidebar."""
    name = (chat or "").strip()
    if follow_up:
        if name.lower() in {"", "new", "current"}:
            return "current"
        return name
    if not name or name.lower() == "current":
        return "current"
    if name.lower() == "new":
        return "new"
    return name


def list_chats() -> list[str]:
    """Read chat titles from the open Cursor Agents Window sidebar."""
    if sys.platform != "darwin":
        return []
    try:
        raw = _osascript(LIST_CHATS_SCRIPT)
    except DesktopError:
        return []
    return parse_chat_names(raw)


LIST_CHATS_SCRIPT = r"""
tell application "Cursor" to activate
delay 0.4
tell application "System Events"
  if not (exists process "Cursor") then return ""
  tell process "Cursor"
    set frontmost to true
    set acc to {}
    repeat with w in windows
      try
        repeat with b in (every button of w)
          try
            set end of acc to (name of b as text)
          end try
        end repeat
      end try
      try
        repeat with b in (every button of every group of w)
          try
            set end of acc to (name of b as text)
          end try
        end repeat
      end try
      try
        repeat with b in (every button of every group of every group of w)
          try
            set end of acc to (name of b as text)
          end try
        end repeat
      end try
      try
        repeat with b in (every row of every outline of w)
          try
            set end of acc to (name of b as text)
          end try
        end repeat
      end try
      try
        repeat with b in (every row of every table of w)
          try
            set end of acc to (name of b as text)
          end try
        end repeat
      end try
    end repeat
    set out to ""
    repeat with n in acc
      set out to out & (n as text) & linefeed
    end repeat
    return out
  end tell
end tell
"""


def _as_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def cloud_script(*, new_chat: bool = True, chat: str | None = None) -> str:
    """Open Cursor 3 Agents Window and send to a chosen Cloud chat.

    chat: "new" starts New Chat, "current" uses the thread already open,
    any other string clicks that sidebar title.
    """
    target = resolve_cloud_target(chat if chat is not None else ("new" if new_chat else "current"))
    if target == "new":
        pick = r"""
    my clickNamed("New Chat")
    delay 0.45
    my clickNamed("Cloud")
    delay 0.4
"""
    elif target == "current":
        pick = r"""
    my clickNamed("Cloud")
    delay 0.35
"""
    else:
        pick = (
            f'\n    my clickNamed("{_as_literal(target)}")\n'
            "    delay 0.45\n"
            '    my clickNamed("Cloud")\n'
            "    delay 0.4\n"
        )
    open_agents = r"""
    try
      click menu item "New Agents Window" of menu "File" of menu bar 1
    end try
    delay 0.3
    try
      click menu item "New Agent Window" of menu "File" of menu bar 1
    end try
    delay 0.2
    try
      click menu item "Open Agents Window" of menu "File" of menu bar 1
    end try
    delay 0.4
""" + pick
    return rf"""
on clickNamed(wanted)
  tell application "System Events"
    tell process "Cursor"
      repeat with w in windows
        set spots to {{w}}
        try
          set spots to spots & (every group of w)
        end try
        try
          set spots to spots & (every group of every group of w)
        end try
        try
          set spots to spots & (every splitter group of w)
        end try
        try
          set spots to spots & (every scroll area of w)
        end try
        repeat with spot in spots
          try
            click (first button of spot whose name is wanted)
            return true
          end try
          try
            click (first pop up button of spot whose name is wanted)
            return true
          end try
          try
            click (first pop up button of spot whose name contains wanted)
            return true
          end try
          try
            click (first UI element of spot whose name is wanted)
            return true
          end try
          try
            click (first UI element of spot whose name contains wanted)
            return true
          end try
        end repeat
      end repeat
    end tell
  end tell
  return false
end clickNamed

tell application "Cursor" to activate
delay 0.8
tell application "System Events"
  if not (exists process "Cursor") then error "Cursor desktop is not running."
  tell process "Cursor"
    set frontmost to true
    delay 0.3
{open_agents}
    try
      set areas to text areas of window 1
      if (count of areas) > 0 then
        click last item of areas
      end if
    end try
    delay 0.25
    try
      set areas to text areas of every group of window 1
      if (count of areas) > 0 then
        click last item of areas
      end if
    end try
    delay 0.2
    keystroke "a" using {{command down}}
    delay 0.1
    keystroke "v" using {{command down}}
    delay 0.4
    key code 36
  end tell
end tell
"""


def send_prompt(*, kind: str = "agent", new_chat: bool = True, chat: str | None = None) -> None:
    if kind == "cloud":
        _osascript(cloud_script(new_chat=new_chat, chat=chat))
        return
    _osascript(agent_script(new_chat=new_chat))


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
