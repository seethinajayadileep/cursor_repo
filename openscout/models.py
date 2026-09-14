from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["critical", "major", "minor", "info"]
StepStatus = Literal["passed", "failed", "skipped"]
RunStatus = Literal["passed", "failed", "running", "error"]


@dataclass
class Action:
    type: str
    target: str = ""
    value: str = ""
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Journey:
    name: str
    steps: list[Action]
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "source": self.source, "steps": [s.to_dict() for s in self.steps]}


@dataclass
class Element:
    id: int
    tag: str
    type: str = ""
    role: str = ""
    text: str = ""
    name: str = ""
    href: str = ""
    placeholder: str = ""
    aria: str = ""
    testid: str = ""
    label: str = ""
    disabled: bool = False
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0

    @property
    def accessible_name(self) -> str:
        return self.label or self.aria or self.text or self.placeholder or self.name

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Snapshot:
    url: str
    title: str
    text: str
    elements: list[Element]
    images: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "elements": [e.to_dict() for e in self.elements],
            "images": self.images,
        }


@dataclass
class StepResult:
    index: int
    raw: str
    action: Action
    status: StepStatus
    message: str
    duration_ms: int
    screenshot: str | None = None
    locator: str | None = None
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.to_dict()
        return data


@dataclass
class Finding:
    id: str
    severity: Severity
    kind: str
    title: str
    detail: str
    url: str
    screenshot: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunReport:
    id: str
    mode: str
    base_url: str
    status: RunStatus
    started_at: str
    finished_at: str
    steps: list[StepResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    pages_visited: list[str] = field(default_factory=list)
    generated_test: str | None = None
    output_dir: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "base_url": self.base_url,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "steps": [s.to_dict() for s in self.steps],
            "findings": [f.to_dict() for f in self.findings],
            "pages_visited": self.pages_visited,
            "generated_test": self.generated_test,
            "output_dir": self.output_dir,
            "error": self.error,
            "summary": {
                "steps": len(self.steps),
                "passed_steps": sum(1 for s in self.steps if s.status == "passed"),
                "failed_steps": sum(1 for s in self.steps if s.status == "failed"),
                "findings": len(self.findings),
                "critical": sum(1 for f in self.findings if f.severity == "critical"),
                "major": sum(1 for f in self.findings if f.severity == "major"),
            },
        }
