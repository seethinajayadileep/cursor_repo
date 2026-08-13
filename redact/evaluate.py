"""Score detections against a hand-labeled gold set.

Span matching is case-insensitive and ignores extra whitespace.
A predicted span is a true positive when its normalised text equals a gold
span of the same type on the same page (or on the synthetic fixture).

Accuracy is token-level on the evaluated pages:
    token is PII if it sits inside a gold/predicted span.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from redact.apply import resolve_overlaps
from redact.detectors import detect_all
from redact.extract import clean_page_text

ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "data" / "gold_labels.json"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def load_gold(path: Path = GOLD_PATH) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _gold_keys(page_labels: list[dict]) -> set[tuple[str, str]]:
    return {(_norm(item["text"]), item["type"]) for item in page_labels}


def _pred_keys(text: str) -> set[tuple[str, str]]:
    spans = resolve_overlaps(detect_all(text))
    return {(_norm(span["text"]), span["type"]) for span in spans}


def _same_span(pred: tuple[str, str], gold: tuple[str, str]) -> bool:
    """Exact type match; text may be equal or one may contain the other."""
    pred_text, pred_type = pred
    gold_text, gold_type = gold
    if pred_type != gold_type:
        return False
    if pred_text == gold_text:
        return True
    shorter, longer = sorted([pred_text, gold_text], key=len)
    return len(shorter) >= 10 and shorter in longer


def _token_flags(text: str, keys: set[tuple[str, str]]) -> list[bool]:
    """Mark whitespace tokens that belong to a (text, type) key."""
    tokens = text.split()
    flags = [False] * len(tokens)
    lowered = [_norm(tok) for tok in tokens]
    # Reconstruct using gold/pred phrases.
    haystack = " ".join(lowered)
    for phrase, _ptype in keys:
        if not phrase:
            continue
        start = 0
        while True:
            idx = haystack.find(phrase, start)
            if idx < 0:
                break
            # Map character offset back to token index.
            prefix = haystack[:idx]
            token_start = len(prefix.split()) if prefix.strip() else 0
            if prefix.endswith(" ") or idx == 0:
                width = len(phrase.split())
                for i in range(token_start, min(token_start + width, len(flags))):
                    flags[i] = True
            start = idx + 1
    return flags


def _align(pred: set[tuple[str, str]], gold: set[tuple[str, str]]):
    """Greedy 1-1 match of predicted spans to gold spans."""
    unmatched_gold = set(gold)
    tp_pred: set[tuple[str, str]] = set()
    for item in sorted(pred, key=lambda x: -len(x[0])):
        hit = next((g for g in unmatched_gold if _same_span(item, g)), None)
        if hit is not None:
            tp_pred.add(item)
            unmatched_gold.remove(hit)
    return tp_pred, pred - tp_pred, unmatched_gold


def score_text(text: str, gold_items: list[dict]) -> dict:
    gold = _gold_keys(gold_items)
    pred = _pred_keys(text)
    tp_set, fp_set, fn_set = _align(pred, gold)
    tp, fp, fn = len(tp_set), len(fp_set), len(fn_set)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    gold_flags = _token_flags(text, gold)
    pred_flags = _token_flags(text, pred)
    token_tp = token_fp = token_fn = token_tn = 0
    for g, p in zip(gold_flags, pred_flags):
        if g and p:
            token_tp += 1
        elif p and not g:
            token_fp += 1
        elif g and not p:
            token_fn += 1
        else:
            token_tn += 1
    total = token_tp + token_fp + token_fn + token_tn
    accuracy = (token_tp + token_tn) / total if total else 1.0

    by_type: dict[str, dict] = {}
    types = {t for _, t in gold | pred}
    for pii_type in sorted(types):
        tps = sum(1 for item in tp_set if item[1] == pii_type)
        fps = sum(1 for item in fp_set if item[1] == pii_type)
        fns = sum(1 for item in fn_set if item[1] == pii_type)
        by_type[pii_type] = {
            "tp": tps,
            "fp": fps,
            "fn": fns,
            "precision": tps / (tps + fps) if (tps + fps) else 1.0,
            "recall": tps / (tps + fns) if (tps + fns) else 1.0,
        }

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "by_type": by_type,
        "false_positives": sorted(fp_set),
        "false_negatives": sorted(fn_set),
    }


def evaluate_pages(original_pages: list[str], gold: dict | None = None) -> dict:
    gold = gold or load_gold()
    per_page = []
    totals = defaultdict(int)
    type_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for spec in gold.get("pages", []):
        page_no = spec["page"]  # 1-based
        if page_no < 1 or page_no > len(original_pages):
            continue
        text = original_pages[page_no - 1]
        result = score_text(text, spec["spans"])
        result["page"] = page_no
        per_page.append(result)
        for key in ("tp", "fp", "fn"):
            totals[key] += result[key]
        for pii_type, stats in result["by_type"].items():
            for key in ("tp", "fp", "fn"):
                type_totals[pii_type][key] += stats[key]

    synthetic_scores = []
    for item in gold.get("synthetic", []):
        text = clean_page_text(item["text"])
        result = score_text(text, item["spans"])
        result["name"] = item.get("name", "synthetic")
        synthetic_scores.append(result)
        for key in ("tp", "fp", "fn"):
            totals[key] += result[key]
        for pii_type, stats in result["by_type"].items():
            for key in ("tp", "fp", "fn"):
                type_totals[pii_type][key] += stats[key]

    tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    # Macro-average token accuracy across scored units.
    acc_values = [p["accuracy"] for p in per_page] + [s["accuracy"] for s in synthetic_scores]
    accuracy = sum(acc_values) / len(acc_values) if acc_values else 1.0

    by_type = {}
    for pii_type, stats in sorted(type_totals.items()):
        tps, fps, fns = stats["tp"], stats["fp"], stats["fn"]
        by_type[pii_type] = {
            "tp": tps,
            "fp": fps,
            "fn": fns,
            "precision": tps / (tps + fps) if (tps + fps) else 1.0,
            "recall": tps / (tps + fns) if (tps + fns) else 1.0,
        }

    return {
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "by_type": by_type,
        "pages": per_page,
        "synthetic": synthetic_scores,
    }


def render_report(metrics: dict) -> str:
    lines = [
        "# PII redaction evaluation report",
        "",
        "Gold labels were written by hand for a sample of prospectus pages, plus a",
        "synthetic ticket-log snippet that covers SSN, credit card, DOB, and IP",
        "(those types do not appear in the RHP).",
        "",
        "## Overall",
        "",
        f"- **Precision:** {metrics['precision']:.3f}  (TP={metrics['tp']}, FP={metrics['fp']})",
        f"- **Recall:** {metrics['recall']:.3f}  (TP={metrics['tp']}, FN={metrics['fn']})",
        f"- **Accuracy (token-level, mean over scored pages):** {metrics['accuracy']:.3f}",
        "",
        "## By PII type",
        "",
        "| Type | Precision | Recall | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pii_type, stats in metrics["by_type"].items():
        lines.append(
            f"| {pii_type} | {stats['precision']:.3f} | {stats['recall']:.3f} | "
            f"{stats['tp']} | {stats['fp']} | {stats['fn']} |"
        )
    lines += [
        "",
        "## Method",
        "",
        "- Gold set: prospectus pages **1, 5, 6, 39** (cover, issuer page, BRLM contacts, summary)",
        "  plus one synthetic ticket-log line for SSN / card / DOB / IP.",
        "- A predicted span matches gold when type agrees and normalised text is identical",
        "  (or one text contains the other, minimum 10 characters — used for addresses).",
        "- Token-level accuracy: each whitespace token on those pages is PII or not;",
        "  accuracy = (TP + TN) / all tokens, then averaged across scored pages.",
        "- CIN, PAN, DIN, rupee amounts, share counts, page numbers, and statute names",
        "  were **not** labeled as PII.",
        "- `CARE Report` was not labeled as a company (it is a document title).",
        "- These scores are for the labeled sample, not the full 130-page PDF.",
        "",
        "## Notes",
        "",
    ]
    fps = []
    fns = []
    for page in metrics.get("pages", []):
        fps.extend(page.get("false_positives") or [])
        fns.extend(page.get("false_negatives") or [])
    if fps:
        lines.append("Example false positives (predicted, not in gold):")
        for item in fps[:15]:
            lines.append(f"- `{item[0]}` ({item[1]})")
        lines.append("")
    if fns:
        lines.append("Example false negatives (gold, missed):")
        for item in fns[:15]:
            lines.append(f"- `{item[0]}` ({item[1]})")
        lines.append("")
    return "\n".join(lines) + "\n"
