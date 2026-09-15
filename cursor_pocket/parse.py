"""Turn Cursor CLI stream-json lines into compact phone-friendly events."""

from __future__ import annotations

import json
from typing import Any

_MAX_TEXT = 4000


def parse_stream_line(line: str) -> dict[str, Any] | None:
    raw = line.strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {"kind": "log", "text": raw[:_MAX_TEXT]}
    if not isinstance(obj, dict):
        return None
    return summarize_event(obj)


def summarize_event(obj: dict[str, Any]) -> dict[str, Any] | None:
    kind = obj.get("type")
    subtype = obj.get("subtype")

    if kind == "system" and subtype == "init":
        model = obj.get("model") or "Cursor"
        cwd = obj.get("cwd") or ""
        text = f"Using {model}"
        if cwd:
            text += f" in {cwd}"
        return {
            "kind": "system",
            "text": text,
            "model": obj.get("model"),
            "session_id": obj.get("session_id"),
        }

    if kind == "assistant":
        if obj.get("model_call_id") is not None:
            return None
        if "timestamp_ms" not in obj and obj.get("message"):
            # Final flush without timestamp is a duplicate of streamed text.
            # Keep it only when we have no streaming timestamps at all.
            pass
        text = _message_text(obj.get("message"))
        if not text:
            return None
        streaming = "timestamp_ms" in obj and "model_call_id" not in obj
        return {"kind": "assistant", "text": text[:_MAX_TEXT], "delta": streaming}

    if kind == "tool_call":
        name, detail = _tool_summary(obj.get("tool_call") or {})
        verb = "started" if subtype == "started" else "done"
        text = f"{name} {verb}"
        if detail:
            text += f" · {detail}"
        return {
            "kind": "tool",
            "text": text[:_MAX_TEXT],
            "tool": name,
            "subtype": subtype,
        }

    if kind == "result":
        result = obj.get("result") or ""
        error = bool(obj.get("is_error"))
        return {
            "kind": "result",
            "text": str(result)[:_MAX_TEXT],
            "error": error,
            "duration_ms": obj.get("duration_ms"),
            "session_id": obj.get("session_id"),
        }

    if kind == "user":
        return None

    return None


def _message_text(message: Any) -> str:
    if not isinstance(message, dict):
        return ""
    parts: list[str] = []
    content = message.get("content") or []
    if isinstance(content, str):
        return content
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
        elif isinstance(item, str):
            parts.append(item)
    return "".join(parts)


def _tool_summary(tool_call: dict[str, Any]) -> tuple[str, str]:
    if "readToolCall" in tool_call:
        args = (tool_call["readToolCall"] or {}).get("args") or {}
        return "read", str(args.get("path") or "")
    if "writeToolCall" in tool_call:
        block = tool_call["writeToolCall"] or {}
        args = block.get("args") or {}
        result = ((block.get("result") or {}).get("success") or {})
        path = result.get("path") or args.get("path") or ""
        extra = ""
        if result.get("linesCreated") is not None:
            extra = f"{result['linesCreated']} lines"
        return "write", " ".join(p for p in (str(path), extra) if p)
    if "function" in tool_call:
        fn = tool_call["function"] or {}
        return str(fn.get("name") or "tool"), ""
    keys = [k for k in tool_call.keys() if k.endswith("ToolCall") or k]
    if keys:
        name = keys[0].replace("ToolCall", "")
        return name, ""
    return "tool", ""
