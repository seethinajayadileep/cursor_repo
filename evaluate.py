#!/usr/bin/env python3
"""Gold-standard evaluation of the PII redactor.

Gold labels come from sample_data.py (the same fixture that builds the source
document). Metrics are entity-level exact match on (type, value):

    precision = TP / (TP + FP)
    recall    = TP / (TP + FN)
    accuracy  = (TP + TN) / (TP + TN + FP + FN)

TN is the count of operational IDs / corporate facts that were correctly
left untouched. Ticket and order numbers are not treated as PII.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from redact import Redactor, extract_docx_text, redact_docx
from sample_data import NON_PII, PREFERRED_FAKES, gold_entities

DEFAULT_SOURCE = Path("data/red_herring_prospectus.docx")
DEFAULT_OUTPUT = Path("output/redacted_prospectus.docx")
DEFAULT_REPORT = Path("output/evaluation_report.md")
DEFAULT_LOG = Path("output/redaction_log.json")


def normalize(value: str) -> str:
    return " ".join(value.split())


def metrics(tp: int, fp: int, fn: int, tn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def evaluate(source: Path, output: Path) -> dict:
    redactor = Redactor(preferred=PREFERRED_FAKES, seed=42)
    findings = redact_docx(source, output, redactor)
    redacted_text = extract_docx_text(output)

    gold = {(g["type"], normalize(g["value"])) for g in gold_entities()}
    detected = {(f.pii_type, normalize(f.original)) for f in findings}

    tp_set = gold & detected
    fp_set = detected - gold
    fn_set = gold - detected

    leftover = []
    for pii_type, value in sorted(gold):
        if value and value in redacted_text:
            leftover.append({"type": pii_type, "value": value})

    preserved = []
    leaked_non_pii = []
    for item in NON_PII:
        if item in redacted_text:
            preserved.append(item)
        else:
            leaked_non_pii.append(item)

    overall = metrics(len(tp_set), len(fp_set), len(fn_set), len(preserved))

    per_type = {}
    types = sorted({t for t, _ in gold | detected})
    for pii_type in types:
        g = {v for t, v in gold if t == pii_type}
        d = {v for t, v in detected if t == pii_type}
        per_type[pii_type] = metrics(len(g & d), len(d - g), len(g - d), 0)
        per_type[pii_type]["gold"] = sorted(g)
        per_type[pii_type]["detected"] = sorted(d)
        per_type[pii_type]["false_positives"] = sorted(d - g)
        per_type[pii_type]["false_negatives"] = sorted(g - d)

    counts = defaultdict(int)
    for finding in findings:
        counts[finding.pii_type] += 1

    result = {
        "source": str(source),
        "output": str(output),
        "gold_unique_entities": len(gold),
        "detected_unique_entities": len(detected),
        "occurrence_replacements": dict(counts),
        "overall": overall,
        "per_type": per_type,
        "true_positives": sorted(tp_set),
        "false_positives": sorted(fp_set),
        "false_negatives": sorted(fn_set),
        "leftover_gold_in_output": leftover,
        "non_pii_preserved": preserved,
        "non_pii_lost": leaked_non_pii,
        "occurrence_recall": 1.0 - (len(leftover) / len(gold) if gold else 0.0),
    }
    return result, findings


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_report(result: dict) -> str:
    overall = result["overall"]
    lines = [
        "# PII Redaction Evaluation Report",
        "",
        "## Evaluation approach",
        "",
        "The sample Red Herring Prospectus (with an investor ticket-log appendix) is generated from a labeled fixture in `sample_data.py`. That fixture is the gold standard: every name, email, phone, company, address, SSN, credit card, date of birth, and IP is known before the redactor runs.",
        "",
        "**Scope choice:** Ticket IDs (`TKT-*`), Order IDs (`ORD-*`), application numbers (`APP-*`), the CIN, regulator names (SEBI), and corporate event dates (prospectus date, incorporation date) are **not** treated as PII. They are the true-negative set.",
        "",
        "Matching is entity-level exact match on `(pii_type, value)` after whitespace normalization. Occurrence recall is a second check: gold strings must not remain in the redacted .docx.",
        "",
        f"- Source: `{result['source']}`",
        f"- Output: `{result['output']}`",
        f"- Gold unique entities: {result['gold_unique_entities']}",
        f"- Detected unique entities: {result['detected_unique_entities']}",
        "",
        "## Overall metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| True positives | {overall['tp']} |",
        f"| False positives | {overall['fp']} |",
        f"| False negatives | {overall['fn']} |",
        f"| True negatives (kept operational IDs) | {overall['tn']} |",
        f"| **Precision** | **{pct(overall['precision'])}** |",
        f"| **Recall** | **{pct(overall['recall'])}** |",
        f"| F1 | {pct(overall['f1'])} |",
        f"| **Accuracy** | **{pct(overall['accuracy'])}** |",
        f"| Occurrence leak check (gold still in output) | {len(result['leftover_gold_in_output'])} leftover |",
        "",
        "## Metrics by PII type",
        "",
        "| Type | Gold | TP | FP | FN | Precision | Recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for pii_type, row in result["per_type"].items():
        gold_n = len(row["gold"])
        lines.append(
            f"| {pii_type} | {gold_n} | {row['tp']} | {row['fp']} | {row['fn']} | "
            f"{pct(row['precision'])} | {pct(row['recall'])} |"
        )

    lines += [
        "",
        "## False positives",
        "",
    ]
    if result["false_positives"]:
        for pii_type, value in result["false_positives"]:
            lines.append(f"- `{pii_type}`: {value}")
    else:
        lines.append("None.")

    lines += [
        "",
        "## False negatives",
        "",
    ]
    if result["false_negatives"]:
        for pii_type, value in result["false_negatives"]:
            lines.append(f"- `{pii_type}`: {value}")
    else:
        lines.append("None.")

    lines += [
        "",
        "## Non-PII preservation",
        "",
        f"Preserved {len(result['non_pii_preserved'])} / {len(result['non_pii_preserved']) + len(result['non_pii_lost'])} operational identifiers and corporate facts.",
        "",
    ]
    if result["non_pii_lost"]:
        lines.append("Lost (should have been kept):")
        for item in result["non_pii_lost"]:
            lines.append(f"- {item}")
    else:
        lines.append("All ticket, order, CIN, and corporate-fact strings remain in the redacted file.")

    lines += [
        "",
        "## Replacement counts (occurrences, including repeats)",
        "",
        "| Type | Replacements |",
        "| --- | ---: |",
    ]
    for pii_type, count in sorted(result["occurrence_replacements"].items()):
        lines.append(f"| {pii_type} | {count} |")

    lines += [
        "",
        "## Notes",
        "",
        "- These figures are measured on the labeled sample prospectus (33 unique PII entities, 20 true-negative operational IDs). They are not a claim of 100% performance on an arbitrary 400-page commercial RHP.",
        "- Dates of birth are redacted only when anchored by `Date of Birth` / `DOB` / `born on`, so filing dates such as August 13, 2026 are kept.",
        "- Credit cards require a Luhn checksum so long digit strings that are not card numbers are not redacted.",
        "- Person names use Title-Case matching plus a stopword list; a gazetteer/NER model would catch rarer names at the cost of more code and more false positives on headings.",
        "- Websites/domains (for example `www.novatechanalytics.example`) are left intact; only email addresses are redacted.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the PII redactor.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    args = parser.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        from build_sample import build

        build()

    result, findings = evaluate(source, Path(args.output))
    report = render_report(result)

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(report, encoding="utf-8")
    Path(args.log).write_text(
        json.dumps(
            {
                **{k: v for k, v in result.items() if k != "per_type"},
                "per_type": {
                    t: {k: v for k, v in row.items() if k not in {"gold", "detected"}}
                    for t, row in result["per_type"].items()
                },
                "replacements": [
                    {
                        "type": f.pii_type,
                        "original": f.original,
                        "replacement": f.replacement,
                    }
                    for f in findings
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    overall = result["overall"]
    print(report)
    print(
        f"precision={pct(overall['precision'])}  "
        f"recall={pct(overall['recall'])}  "
        f"accuracy={pct(overall['accuracy'])}"
    )
    print(f"Wrote {args.report}")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
