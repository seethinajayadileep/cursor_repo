from __future__ import annotations

import json
from pathlib import Path

from openscout.models import RunReport


def write_reports(report: RunReport, run_dir: Path) -> None:
    data = report.to_dict()
    (run_dir / "report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    (run_dir / "report.html").write_text(render_html(report), encoding="utf-8")


def render_markdown(report: RunReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        f"# OpenScout report — {report.id}",
        "",
        f"- Mode: `{report.mode}`",
        f"- Status: **{report.status}**",
        f"- Target: {report.base_url}",
        f"- Started: {report.started_at}",
        f"- Finished: {report.finished_at}",
        f"- Steps: {summary['passed_steps']}/{summary['steps']} passed",
        f"- Findings: {summary['findings']} ({summary['critical']} critical, {summary['major']} major)",
        "",
        "## Steps",
        "",
    ]
    for step in report.steps:
        mark = "PASS" if step.status == "passed" else "FAIL"
        lines.append(f"- `{mark}` {step.raw or step.action.type} — {step.message}")
    lines += ["", "## Findings", ""]
    if not report.findings:
        lines.append("No findings.")
    for finding in report.findings:
        lines.append(f"- **[{finding.severity}] {finding.title}** ({finding.kind}) at {finding.url}")
        lines.append(f"  - {finding.detail}")
    if report.pages_visited:
        lines += ["", "## Pages visited", ""]
        for url in report.pages_visited:
            lines.append(f"- {url}")
    if report.generated_test:
        lines += ["", "## Generated Playwright test", "", "```python", report.generated_test, "```"]
    if report.error:
        lines += ["", "## Error", "", report.error]
    return "\n".join(lines) + "\n"


def render_html(report: RunReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    status_class = "ok" if report.status == "passed" else "bad"

    def shot(path: str | None) -> str:
        if not path:
            return ""
        return f'<a class="shot" href="{path}"><img src="{path}" alt="screenshot" /></a>'

    steps = []
    for step in report.steps:
        cls = "pass" if step.status == "passed" else "fail"
        steps.append(
            f'<article class="step {cls}">'
            f"<header><span class='pill'>{step.status}</span><code>{_esc(step.raw or step.action.type)}</code>"
            f"<span class='ms'>{step.duration_ms}ms</span></header>"
            f"<p>{_esc(step.message)}</p>{shot(step.screenshot)}</article>"
        )
    findings = []
    for finding in report.findings:
        findings.append(
            f'<article class="finding {finding.severity}">'
            f"<header><span class='pill'>{finding.severity}</span><strong>{_esc(finding.title)}</strong>"
            f"<span class='kind'>{finding.kind}</span></header>"
            f"<p>{_esc(finding.detail)}</p><p class='url'>{_esc(finding.url)}</p>{shot(finding.screenshot)}</article>"
        )
    pages = "".join(f"<li>{_esc(url)}</li>" for url in report.pages_visited)
    generated = ""
    if report.generated_test:
        generated = f"<h2>Generated test</h2><pre>{_esc(report.generated_test)}</pre>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>OpenScout {report.id}</title>
  <style>
    :root {{ --bg:#0e1116; --card:#161b22; --text:#e6edf3; --muted:#8b949e; --ok:#3fb950; --bad:#f85149; --warn:#d29922; --line:#30363d; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:15px/1.5 "IBM Plex Sans", ui-sans-serif, system-ui; background:var(--bg); color:var(--text); }}
    main {{ max-width:1080px; margin:0 auto; padding:32px 20px 80px; }}
    h1 {{ font-size:28px; margin:0 0 8px; }}
    .lede {{ color:var(--muted); margin-bottom:24px; }}
    .stats {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:28px; }}
    .stat {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; min-width:120px; }}
    .stat b {{ display:block; font-size:22px; }}
    .ok {{ color:var(--ok); }} .bad {{ color:var(--bad); }}
    .step, .finding {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; margin:12px 0; }}
    .step.fail {{ border-color:#f85149; }}
    .finding.critical {{ border-color:#f85149; }}
    .finding.major {{ border-color:#d29922; }}
    header {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
    .pill {{ font-size:11px; letter-spacing:.04em; text-transform:uppercase; border-radius:999px; padding:2px 8px; border:1px solid var(--line); }}
    .pass .pill {{ color:var(--ok); border-color:var(--ok); }}
    .fail .pill, .critical .pill {{ color:var(--bad); border-color:var(--bad); }}
    .ms, .kind, .url {{ color:var(--muted); font-size:12px; }}
    img {{ max-width:100%; border-radius:8px; border:1px solid var(--line); margin-top:10px; }}
    pre {{ background:#0d1117; border:1px solid var(--line); padding:14px; overflow:auto; border-radius:10px; }}
    code {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size:13px; }}
  </style>
</head>
<body>
<main>
  <p class="lede">OpenScout testing agent</p>
  <h1>Run {report.id}</h1>
  <p class="lede">{_esc(report.mode)} · {_esc(report.base_url)}</p>
  <div class="stats">
    <div class="stat"><span>Status</span><b class="{status_class}">{report.status}</b></div>
    <div class="stat"><span>Steps passed</span><b>{summary['passed_steps']}/{summary['steps']}</b></div>
    <div class="stat"><span>Findings</span><b>{summary['findings']}</b></div>
    <div class="stat"><span>Critical</span><b>{summary['critical']}</b></div>
  </div>
  <h2>Steps</h2>
  {''.join(steps) or '<p>No steps.</p>'}
  <h2>Findings</h2>
  {''.join(findings) or '<p>No findings.</p>'}
  <h2>Pages visited</h2>
  <ul>{pages or '<li>None</li>'}</ul>
  {generated}
</main>
</body>
</html>
"""


def _esc(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
