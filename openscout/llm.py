from __future__ import annotations

import json
from typing import Any

from openscout.config import Settings
from openscout.models import Snapshot


def llm_available(settings: Settings) -> bool:
    return bool(settings.llm_api_key)


def choose_explore_action(snapshot: Snapshot, candidates: list[dict[str, Any]], settings: Settings) -> int | None:
    """Ask an OpenAI-compatible model which candidate to try next. Returns an index or None."""
    if not settings.llm_api_key or not candidates:
        return None
    try:
        import urllib.request

        payload = {
            "model": settings.llm_model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a QA agent picking the next UI action. "
                        "Reply with JSON {\"index\": N} only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "url": snapshot.url,
                            "title": snapshot.title,
                            "candidates": candidates,
                        }
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            settings.llm_base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.llm_api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        if content.strip().startswith("```"):
            content = content.strip().strip("`")
            content = content.split("\n", 1)[-1]
        data = json.loads(content)
        index = int(data["index"])
        if 0 <= index < len(candidates):
            return index
    except Exception:
        return None
    return None
