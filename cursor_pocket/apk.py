"""Locate a built Cursor Pocket APK so the laptop can hand it to the phone."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def apk_path(root: Path | None = None) -> Path | None:
    base = root or ROOT
    candidates = (
        base / "android" / "dist" / "cursor-pocket.apk",
        base / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk",
        base / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk",
    )
    for path in candidates:
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None
