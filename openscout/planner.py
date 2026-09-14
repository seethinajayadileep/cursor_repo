from __future__ import annotations

import re
from pathlib import Path

from openscout.models import Action, Journey

GHERKIN_PREFIX = re.compile(r"^(given|when|then|and|but)\s+", re.I)
SECTION = re.compile(
    r"^(feature|scenario(?:\s+outline)?|examples|background)\s*:",
    re.I,
)

OPEN = re.compile(
    r'^(?:i\s+)?(?:open|go to|navigate to|visit)\s+(?:the\s+page\s+)?["“]?(.+?)["”]?$',
    re.I,
)
CLICK = re.compile(
    r'^(?:i\s+)?(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?["“]?(.+?)["”]?$',
    re.I,
)
FILL = re.compile(
    r'^(?:i\s+)?(?:fill|type|enter|set)\s+(?:the\s+)?["“]?(.+?)["”]?\s+'
    r'(?:with|to|as)\s+["“]?(.+?)["”]?$',
    re.I,
)
TYPE_INTO = re.compile(
    r'^(?:i\s+)?(?:type|enter)\s+["“]?(.+?)["”]?\s+(?:into|in)\s+(?:the\s+)?["“]?(.+?)["”]?(?:\s+field)?$',
    re.I,
)
SELECT = re.compile(
    r'^(?:i\s+)?select\s+["“]?(.+?)["”]?\s+(?:in|from)\s+(?:the\s+)?["“]?(.+?)["”]?$',
    re.I,
)
CHECK = re.compile(r'^(?:i\s+)?(check|uncheck)\s+(?:the\s+)?["“]?(.+?)["”]?$', re.I)
SEE = re.compile(
    r'^(?:i\s+)?(?:should\s+)?(?:see|contain(?:s)?)\s+(?:the\s+text\s+)?["“]?(.+?)["”]?$',
    re.I,
)
PAGE_CONTAINS = re.compile(
    r'^(?:the\s+)?page\s+(?:should\s+)?(?:contain|contains)\s+["“]?(.+?)["”]?$',
    re.I,
)
NOT_SEE = re.compile(
    r'^(?:i\s+)?should\s+not\s+see\s+["“]?(.+?)["”]?$',
    re.I,
)
URL_IS = re.compile(
    r'^(?:the\s+)?url\s+should\s+(be|contain|contains)\s+["“]?(.+?)["”]?$',
    re.I,
)
WAIT = re.compile(r'^(?:i\s+)?wait\s+(\d+(?:\.\d+)?)\s*(s|ms|seconds?|milliseconds?)?$', re.I)
SCREENSHOT = re.compile(r'^(?:i\s+)?(?:take\s+a\s+)?screenshot$', re.I)
NO_CONSOLE = re.compile(
    r'^(?:the\s+page\s+should\s+)?(?:have\s+)?no\s+console\s+errors$',
    re.I,
)
TITLE = re.compile(
    r'^(?:the\s+)?(?:page\s+)?title\s+should\s+(be|contain)\s+["“]?(.+?)["”]?$',
    re.I,
)


def _clean_line(line: str) -> str:
    line = line.strip()
    if line.startswith("|"):
        return ""
    line = GHERKIN_PREFIX.sub("", line)
    return line.strip().rstrip(".")


def _strip_quotes(value: str) -> str:
    return value.strip().strip("\"'“”")


def parse_step(line: str) -> Action | None:
    raw = line.rstrip("\n")
    text = _clean_line(line)
    if not text or SECTION.match(text) or text.startswith("#"):
        return None

    if SCREENSHOT.match(text):
        return Action(type="screenshot", raw=raw)
    if NO_CONSOLE.match(text):
        return Action(type="no_console", raw=raw)

    match = OPEN.match(text)
    if match:
        return Action(type="open", target=_strip_quotes(match.group(1)), raw=raw)

    match = TYPE_INTO.match(text)
    if match:
        return Action(
            type="fill",
            target=_strip_quotes(match.group(2)),
            value=_strip_quotes(match.group(1)),
            raw=raw,
        )

    match = FILL.match(text)
    if match:
        return Action(
            type="fill",
            target=_strip_quotes(match.group(1)),
            value=_strip_quotes(match.group(2)),
            raw=raw,
        )

    match = SELECT.match(text)
    if match:
        return Action(
            type="select",
            target=_strip_quotes(match.group(2)),
            value=_strip_quotes(match.group(1)),
            raw=raw,
        )

    match = CHECK.match(text)
    if match:
        return Action(
            type=match.group(1).lower(),
            target=_strip_quotes(match.group(2)),
            raw=raw,
        )

    match = NOT_SEE.match(text)
    if match:
        return Action(type="not_see", target=_strip_quotes(match.group(1)), raw=raw)

    match = SEE.match(text)
    if match:
        return Action(type="see", target=_strip_quotes(match.group(1)), raw=raw)

    match = PAGE_CONTAINS.match(text)
    if match:
        return Action(type="see", target=_strip_quotes(match.group(1)), raw=raw)

    match = URL_IS.match(text)
    if match:
        op = "url_is" if match.group(1).lower() == "be" else "url_contains"
        return Action(type=op, target=_strip_quotes(match.group(2)), raw=raw)

    match = TITLE.match(text)
    if match:
        op = "title_is" if match.group(1).lower() == "be" else "title_contains"
        return Action(type=op, target=_strip_quotes(match.group(2)), raw=raw)

    match = WAIT.match(text)
    if match:
        amount = float(match.group(1))
        unit = (match.group(2) or "s").lower()
        ms = int(amount if unit.startswith("ms") else amount * 1000)
        return Action(type="wait", value=str(ms), raw=raw)

    match = CLICK.match(text)
    if match:
        target = _strip_quotes(match.group(1))
        target = re.sub(r"\s+(button|link|tab)$", "", target, flags=re.I)
        return Action(type="click", target=target, raw=raw)

    return Action(type="see", target=_strip_quotes(text), raw=raw)


def parse_journey(text: str, source: str = "") -> Journey:
    name = "Untitled journey"
    steps: list[Action] = []
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("feature:"):
            name = stripped.split(":", 1)[1].strip() or name
            continue
        if lower.startswith("scenario"):
            scenario = stripped.split(":", 1)[-1].strip()
            if scenario:
                name = scenario
            continue
        action = parse_step(line)
        if action:
            steps.append(action)
    return Journey(name=name, steps=steps, source=source)


def load_journey(path: str | Path) -> Journey:
    file = Path(path)
    return parse_journey(file.read_text(encoding="utf-8"), source=str(file))
