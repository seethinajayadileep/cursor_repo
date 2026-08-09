#!/usr/bin/env python3
"""Categorize coupon codes by service and emit clean catalogs."""

from __future__ import annotations

import csv
import json
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "coupon-codes" / "raw"
OUT_DIR = ROOT / "coupon-codes" / "by-service"
INDEX_DIR = ROOT / "coupon-codes"

SERVICES = [
    "mobbin",
    "arize",
    "relay_app",
    "magic_pattern",
    "reforge_build",
    "descript",
    "bolt_new",
    "deepsky",
]

DISPLAY = {
    "mobbin": "Mobbin",
    "arize": "Arize",
    "relay_app": "Relay.app",
    "magic_pattern": "Magic Patterns",
    "reforge_build": "Reforge Build",
    "descript": "Descript",
    "bolt_new": "Bolt.new",
    "deepsky": "DeepSky",
}

LINKS = {
    "speechify": (
        "https://speechify.com/onboarding/activate?groupCode="
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJ0ZWFtSWQiOiJlNDgyOGNlYi01MTc5LTQ0MTQtYTdiMS03OTQ3NmExMDIyNzki"
        "LCJ0ZWFtTmFtZSI6IkFha2FzaCdzIEJ1bmRsZSIsImlhdCI6MTc3MjA1NjE1MSwi"
        "ZXhwIjoxNzc0NjQ4MTUxfQ.jYOmEcxCVNM9ownCvYmmmdpM1PTAVuCyPeTLGWigebM"
    ),
    "dovetail": "https://dovetail.com/p/aakash-bundle/",
    "linear": "https://linear.app/coupon/productgrowth",
    "drive_folders": [
        "https://drive.google.com/drive/folders/1k5WWTePOOiYyPU6_HCzcWUFh1c5aNfSw?usp=drive_link",
        "https://drive.google.com/file/d/1xs882Woic6o4h2i3eN2ePuK9511MIZy5/view?usp=sharing",
        "https://drive.google.com/drive/folders/1abm0QGcg0zEx3q1yz5iP1Ph5cQCz9WXy?usp=sharing",
        "https://drive.google.com/drive/folders/155BM-IbDYxHwDxk3eqiO2zyzBaqU-2nn",
        "https://drive.google.com/drive/folders/1czW-lqlaU3JZeoc03I7mMpafWHd2lXMP?usp=drive_link",
        "https://drive.google.com/drive/folders/1xXKYPDsxh9ZSRyE_T1Y1r9J3sCPr68hK?usp=drive_link",
        "https://drive.google.com/drive/folders/1vbW0fpUUggMtLZkCm48QC0vabzpnjiqA?usp=sharing",
        "https://drive.google.com/drive/folders/1XxQ7n-okaMjLmlJh8jj0cc8GbwGjwELY?usp=drive_link",
    ],
}

TOKEN_RE = re.compile(
    r"(?:PGXARIZE-[A-Z0-9]+|AAKASH1000-[A-Z0-9]+|AAKASH\d{10,}|AAKASH12|[A-Z0-9]{8})"
)


def extract_codes(text: str) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for match in TOKEN_RE.findall(text.upper()):
        seen.setdefault(match, None)
    return list(seen)


def load_service(service: str) -> list[str]:
    path = RAW_DIR / f"{service}.txt"
    if not path.exists():
        return []
    return extract_codes(path.read_text(encoding="utf-8"))


def arize_subtypes(codes: list[str]) -> dict[str, list[str]]:
    pgx = [c for c in codes if c.startswith("PGXARIZE-") or c.startswith("PGxARIZE-")]
    # normalize: extract kept original upper-case PGxARIZE
    pgx = [c for c in codes if c.startswith("PGXARIZE-")]
    # Our extractor uppercases everything, so prefix becomes PGXARIZE-
    aakash = [c for c in codes if c.startswith("AAKASH1000-")]
    other = [c for c in codes if c not in set(pgx) | set(aakash)]
    return {
        "pgxarize": pgx,
        "aakash1000": aakash,
        "other": other,
    }


def assert_no_duplicates(catalog: dict[str, list[str]]) -> None:
    """Fail the build if any within-service or cross-service duplicates exist."""
    owners: dict[str, str] = {}
    for service, codes in catalog.items():
        if len(codes) != len(set(codes)):
            raise SystemExit(f"Duplicate codes found within {service}")
        for code in codes:
            key = code.upper()
            if key in owners:
                raise SystemExit(
                    f"Cross-service duplicate {code}: {owners[key]} and {service}"
                )
            owners[key] = service


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    catalog: dict[str, list[str]] = {}

    for service in SERVICES:
        codes = load_service(service)
        # Restore PGxARIZE casing for readability
        if service == "arize":
            codes = [
                c.replace("PGXARIZE-", "PGxARIZE-", 1) if c.startswith("PGXARIZE-") else c
                for c in codes
            ]
        # Keep only unique codes, first occurrence wins
        codes = list(OrderedDict.fromkeys(codes))
        catalog[service] = codes
        out_text = "\n".join(codes) + ("\n" if codes else "")
        (OUT_DIR / f"{service}.txt").write_text(out_text, encoding="utf-8")
        # Keep raw sources cleaned to one unique code per line too
        (RAW_DIR / f"{service}.txt").write_text(out_text, encoding="utf-8")

    assert_no_duplicates(catalog)

    # Combined markdown
    md_lines = [
        "# Coupon Codes by Service",
        "",
        "Unique codes categorized from the pasted inventory.",
        "",
        "## Summary",
        "",
        "| Service | Unique codes |",
        "|---|---:|",
    ]
    total = 0
    for service in SERVICES:
        count = len(catalog[service])
        total += count
        md_lines.append(f"| {DISPLAY[service]} | {count} |")
    md_lines.extend(["", f"**Total unique codes:** {total}", ""])

    md_lines.extend(
        [
            "## Link-based freebies",
            "",
            f"- **Speechify:** {LINKS['speechify']}",
            f"- **Dovetail:** {LINKS['dovetail']}",
            f"- **Linear:** {LINKS['linear']}",
            "",
            "### Drive folders",
            "",
        ]
    )
    for url in LINKS["drive_folders"]:
        md_lines.append(f"- {url}")
    md_lines.append("")

    subtypes = arize_subtypes(
        [
            c.replace("PGxARIZE-", "PGXARIZE-", 1) if c.startswith("PGxARIZE-") else c
            for c in catalog["arize"]
        ]
    )
    md_lines.extend(
        [
            "## Arize subtypes",
            "",
            f"- PGxARIZE-*: {len(subtypes['pgxarize'])}",
            f"- AAKASH1000-*: {len(subtypes['aakash1000'])}",
            "",
        ]
    )

    for service in SERVICES:
        md_lines.extend(
            [
                f"## {DISPLAY[service]} ({len(catalog[service])})",
                "",
            ]
        )
        if not catalog[service]:
            md_lines.append("_No codes_")
            md_lines.append("")
            continue
        for code in catalog[service]:
            md_lines.append(f"- `{code}`")
        md_lines.append("")

    (INDEX_DIR / "CATEGORIES.md").write_text("\n".join(md_lines), encoding="utf-8")

    # JSON
    payload = {
        "summary": {DISPLAY[s]: len(catalog[s]) for s in SERVICES},
        "total_unique_codes": total,
        "codes": {DISPLAY[s]: catalog[s] for s in SERVICES},
        "link_freebies": {
            "Speechify": LINKS["speechify"],
            "Dovetail": LINKS["dovetail"],
            "Linear": LINKS["linear"],
            "Drive folders": LINKS["drive_folders"],
        },
        "arize_subtypes": {
            "PGxARIZE": [
                c.replace("PGXARIZE-", "PGxARIZE-", 1) for c in subtypes["pgxarize"]
            ],
            "AAKASH1000": subtypes["aakash1000"],
        },
    }
    (INDEX_DIR / "catalog.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    # CSV flat list
    csv_path = INDEX_DIR / "catalog.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["service", "code"])
        for service in SERVICES:
            for code in catalog[service]:
                writer.writerow([DISPLAY[service], code])

    # Compact all-codes index
    summary_lines = [
        "# Coupon Code Categories",
        "",
        "Organized unique coupon codes by product/service.",
        "",
        "## Counts",
        "",
    ]
    for service in SERVICES:
        summary_lines.append(
            f"- **{DISPLAY[service]}**: {len(catalog[service])} "
            f"(see `by-service/{service}.txt`)"
        )
    summary_lines.extend(
        [
            "",
            f"- **Total**: {total}",
            "",
            "## Link freebies (no per-user code list)",
            "",
            f"- Speechify: {LINKS['speechify']}",
            f"- Dovetail: {LINKS['dovetail']}",
            f"- Linear: {LINKS['linear']}",
            "",
            "## Files",
            "",
            "- `by-service/*.txt` — one unique code per line (duplicates removed)",
            "- `raw/*.txt` — cleaned unique source lists (same codes)",
            "- `catalog.json` — machine-readable full catalog",
            "- `catalog.csv` — flat service,code table",
            "- `CATEGORIES.md` — full markdown listing",
            "",
            "All lists are deduplicated within each service and across services.",
            "",
        ]
    )
    (INDEX_DIR / "README.md").write_text("\n".join(summary_lines), encoding="utf-8")

    # Root README pointer
    (ROOT / "README.md").write_text(
        "\n".join(
            [
                "# Coupon Code Catalog",
                "",
                "Coupon codes from the pasted inventory, categorized by service.",
                "",
                "See [`coupon-codes/README.md`](coupon-codes/README.md) for counts and file layout.",
                "",
                "Rebuild with:",
                "",
                "```bash",
                "python3 scripts/build_catalog.py",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print("Built catalog:")
    for service in SERVICES:
        print(f"  {DISPLAY[service]:16} {len(catalog[service]):5}")
    print(f"  {'TOTAL':16} {total:5}")


if __name__ == "__main__":
    main()
