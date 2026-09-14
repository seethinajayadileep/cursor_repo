from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    headless: bool = True
    timeout_ms: int = 8000
    max_steps: int = 24
    output_dir: Path = Path("runs")
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    slow_mo: int = 0


def load_settings(**overrides: object) -> Settings:
    settings = Settings(
        headless=os.environ.get("OPENSCOUT_HEADED", "").lower() not in {"1", "true", "yes"},
        timeout_ms=int(os.environ.get("OPENSCOUT_TIMEOUT_MS", "8000")),
        max_steps=int(os.environ.get("OPENSCOUT_MAX_STEPS", "24")),
        output_dir=Path(os.environ.get("OPENSCOUT_OUTPUT", "runs")),
        llm_api_key=os.environ.get("OPENSCOUT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        llm_base_url=os.environ.get("OPENSCOUT_LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_model=os.environ.get("OPENSCOUT_LLM_MODEL", "gpt-4o-mini"),
    )
    for key, value in overrides.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)
    return settings
