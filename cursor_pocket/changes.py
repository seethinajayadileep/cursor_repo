"""Summarize what Cursor changed on disk so the phone can show the fix."""

from __future__ import annotations

import subprocess
from pathlib import Path

_MAX_DIFF = 8000


def snapshot(workspace: str) -> str:
    return _run(workspace, ["status", "--porcelain", "-uall"]) + "\n" + _run(workspace, ["diff", "HEAD"])


def describe_changes(workspace: str, before: str) -> dict[str, str | list[str]]:
    after = snapshot(workspace)
    if after == before:
        return {"text": "Cursor did not change any files.", "files": [], "diff": ""}
    names = _changed_files(workspace)
    diff = _run(workspace, ["diff", "HEAD", "--stat"])
    full = _run(workspace, ["diff", "HEAD"])
    extra = _untracked(workspace)
    lines = []
    if names:
        lines.append("Files Cursor changed:")
        lines.extend(f"  • {name}" for name in names)
    if extra:
        lines.append("New files:")
        lines.extend(f"  • {name}" for name in extra)
        names = list(dict.fromkeys([*names, *extra]))
    if diff.strip():
        lines.append("")
        lines.append(diff.strip())
    body = "\n".join(lines).strip() or "Cursor updated the project."
    clipped = full[:_MAX_DIFF]
    if len(full) > _MAX_DIFF:
        clipped += "\n… (truncated)"
    text = body
    if clipped.strip():
        text = f"{body}\n\nWhat changed:\n{clipped}"
    return {"text": text, "files": names, "diff": clipped}


def _changed_files(workspace: str) -> list[str]:
    raw = _run(workspace, ["diff", "HEAD", "--name-only"])
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _untracked(workspace: str) -> list[str]:
    raw = _run(workspace, ["ls-files", "--others", "--exclude-standard"])
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _run(workspace: str, args: list[str]) -> str:
    root = Path(workspace)
    git = root / ".git"
    if not git.exists():
        return ""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout or ""
