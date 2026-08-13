#!/usr/bin/env python3
"""Regex-based PII redactor for .docx (and plain text).

Detects names, emails, phones, companies, addresses, SSNs, credit cards,
dates of birth, and IP addresses, then replaces each value with a stable
fake alternative (same input always maps to the same fake).

Ticket / order / CIN / application numbers are left unchanged on purpose.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from docx import Document
from faker import Faker

DEFAULT_PREFERRED = {
    "Rashi Patil": "John Doe",
    "rashhi.patil@gmail.com": "john.doe@example.com",
    "Rohan Dey": "Peter Parker",
    "rohan.dey@gmail.com": "peter.parker@example.com",
    "+91 9876543210": "+91 1234567645",
}

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CC_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
IP_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\b"
)

PHONE_RES = [
    re.compile(r"(?<!\d)\+91[\s-]*[6-9]\d{4}[\s-]\d{5}(?!\d)"),
    re.compile(r"(?<!\d)\+91[\s-]*[6-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\+1[\s.\-]*\(?\d{3}\)?[\s.\-]*\d{3}[\s.\-]*\d{4}(?!\d)"),
    re.compile(r"\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}"),
]

MONTHS = (
    r"(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)"
)
DATE = (
    rf"(?:\d{{1,2}}\s+{MONTHS}\s+\d{{4}}|{MONTHS}\s+\d{{1,2}},?\s+\d{{4}}|"
    rf"\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}|\d{{4}}-\d{{2}}-\d{{2}})"
)
DOB_RE = re.compile(
    rf"\b(?:Date of Birth|D\.?O\.?B\.?|born(?:\s+on)?)\s*[:\-]?\s*({DATE})",
    re.I,
)

ADDRESS_LABEL_RE = re.compile(
    r"(?:Registered(?:\s+and\s+Corporate)?\s+Office|Corporate\s+Office|Address)\s*:\s*",
    re.I,
)
STREET_RE = re.compile(
    r"\b(?:Flat\s+)?\d{1,4}[A-Za-z]?[,\s]+.{0,80}?"
    r"(?:Road|Street|Marg|Nagar|Lane|Towers|Apartments|Galli|"
    r"Avenue|Drive|Grove|Plaza|House|Enclave|Layout|Residency)\b"
    r".{0,90}?\b\d{6}\b"
    r"(?:,\s*[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})?",
    re.I,
)

# Spaces only (not newlines) so headings on the previous line are not swallowed.
_SP = r"[ \t]+"
COMPANY_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z0-9&'\-]+" + _SP + r"){0,5}[A-Z][A-Za-z0-9&'\-]+" + _SP
    + r"(?:Private" + _SP + r"Limited|Pvt\.?" + _SP + r"?Ltd\.?|Limited|Ltd\.?|"
    r"LLP|LLC|Inc\.|Corp\.|Corporation))"
)
COMPANY_LEAD_STOP = {
    "book", "built", "issue", "red", "herring", "prospectus", "confidential",
    "sample", "filing", "for", "pii", "redaction", "dated", "please", "read",
    "section", "our", "the", "and", "of", "this", "initial", "public",
    "offering", "appendix", "investor", "support", "ticket", "log", "behalf",
}

NAME_TOKEN = r"[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?"
NAME_RE = re.compile(rf"\b({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{1,2}})\b")
HONORIFIC_RE = re.compile(
    rf"\b(?:Mr|Mrs|Ms|Miss|Dr|Shri|Smt)\.?\s+({NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}})\b"
)

# Words that look Title-Case but are not person names in this domain.
NAME_STOP = {
    "red", "herring", "prospectus", "private", "limited", "company", "public",
    "offer", "issue", "equity", "share", "shares", "board", "directors",
    "director", "independent", "executive", "whole", "time", "officer",
    "secretary", "compliance", "contact", "person", "registered", "office",
    "corporate", "initial", "book", "built", "appendix", "investor",
    "support", "ticket", "order", "status", "open", "please", "read",
    "section", "companies", "act", "dated", "floor", "road", "street",
    "towers", "apartments", "view", "lake", "salt", "palm", "grove",
    "sunrise", "linking", "bandra", "west", "east", "north", "south",
    "mumbai", "bengaluru", "kolkata", "pune", "maharashtra", "karnataka",
    "india", "email", "website", "promoters", "chapter", "annexure",
    "schedule", "table", "contents", "page", "face", "value", "price",
    "premium", "million", "rupees", "cash", "application", "allotment",
    "listing", "stock", "exchange", "securities", "registrar", "draft",
    "tech", "analytics", "digital", "consulting", "nova", "baker",
    "residency", "shivajinagar", "koramangala", "juhu", "sector", "flat",
    "chief", "financial", "source", "message", "refund", "update",
    "built", "issue", "equity", "shares", "offer", "this", "that",
    "from", "with", "your", "our", "the", "and", "for", "non",
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december", "redacted",
    "house", "plaza", "enclave", "layout", "residency", "apartments",
    "private", "limited", "llp", "llc", "inc", "corp", "telephone",
    "identity", "number", "dated", "please", "read", "appendix",
    "ticket", "log", "investor", "support", "kyc", "card", "ending",
    "social", "security", "address", "phone", "birth", "date",
    "whole-time", "non-executive", "independent", "morning", "hello",
    "kindly", "please", "thanks", "regards", "team", "customer",
    "service", "status", "open", "closed", "pending", "india",
}

PRIORITY = {
    "email": 10,
    "credit_card": 20,
    "ssn": 30,
    "phone": 40,
    "ip_address": 50,
    "date_of_birth": 60,
    "address": 70,
    "company": 80,
    "name": 90,
}


@dataclass
class Finding:
    pii_type: str
    original: str
    replacement: str
    start: int
    end: int


def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", number)]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _spans(regexes, text):
    if not isinstance(regexes, list):
        regexes = [regexes]
    out = []
    for regex in regexes:
        for match in regex.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            start = match.start(1) if match.lastindex else match.start()
            end = match.end(1) if match.lastindex else match.end()
            out.append((start, end, value))
    return out


def find_emails(text):
    return _spans(EMAIL_RE, text)


def find_ssns(text):
    return _spans(SSN_RE, text)


def find_credit_cards(text):
    return [(s, e, v) for s, e, v in _spans(CC_RE, text) if luhn_ok(v)]


def find_phones(text):
    return _spans(PHONE_RES, text)


def find_ips(text):
    found = []
    for start, end, value in _spans(IP_RE, text):
        ctx = text[max(0, start - 16) : start].lower()
        if "version" in ctx or re.search(r"\bv\s*$", ctx):
            continue
        found.append((start, end, value))
    return found


def find_dobs(text):
    return _spans(DOB_RE, text)


def find_addresses(text):
    found = []
    for match in ADDRESS_LABEL_RE.finditer(text):
        rest = text[match.end() :]
        line = rest.split("\n")[0]
        cut = re.search(r"\s+(?:Tel:|Email:|Phone:|Website:|CIN:)", line)
        if cut:
            line = line[: cut.start()]
        value = line.rstrip()
        if len(value) >= 12:
            found.append((match.end(), match.end() + len(value), value))
    found.extend(_spans(STREET_RE, text))
    return found


def find_companies(text):
    found = []
    for match in COMPANY_RE.finditer(text):
        value = match.group(1)
        start, end = match.start(1), match.end(1)
        while True:
            parts = re.split(r"([ \t]+)", value, maxsplit=1)
            if len(parts) < 3:
                break
            word, sep, rest = parts
            if word.lower().strip(".,") in COMPANY_LEAD_STOP:
                start += len(word) + len(sep)
                value = rest
            else:
                break
        if value:
            found.append((start, end, value))
    return found


def find_names(text):
    found = []
    for start, end, value in _spans([HONORIFIC_RE, NAME_RE], text):
        parts = value.split()
        if any(part.lower() in NAME_STOP for part in parts):
            continue
        if any(len(part) < 2 for part in parts):
            continue
        found.append((start, end, value))
    return found


DETECTORS = [
    ("email", find_emails),
    ("credit_card", find_credit_cards),
    ("ssn", find_ssns),
    ("phone", find_phones),
    ("ip_address", find_ips),
    ("date_of_birth", find_dobs),
    ("address", find_addresses),
    ("company", find_companies),
    ("name", find_names),
]


def merge_spans(matches: list[Finding]) -> list[Finding]:
    """Keep longer / higher-priority spans when they overlap."""
    ordered = sorted(
        matches,
        key=lambda m: (m.start, -(m.end - m.start), PRIORITY.get(m.pii_type, 99)),
    )
    kept: list[Finding] = []
    for item in ordered:
        if any(item.start < k.end and item.end > k.start for k in kept):
            continue
        kept.append(item)
    return sorted(kept, key=lambda m: m.start)


class Redactor:
    def __init__(self, preferred=None, seed: int = 42):
        self.preferred = dict(DEFAULT_PREFERRED)
        if preferred:
            self.preferred.update(preferred)
        self.mapping: dict[tuple[str, str], str] = {}
        self.faker = Faker("en_US")
        self.faker.seed_instance(seed)
        Faker.seed(seed)

    def fake_for(self, pii_type: str, original: str) -> str:
        if original in self.preferred:
            return self.preferred[original]
        key = (pii_type, original)
        if key not in self.mapping:
            self.mapping[key] = self._generate(pii_type, original)
        return self.mapping[key]

    def _generate(self, pii_type: str, original: str) -> str:
        fake = self.faker
        if pii_type == "name":
            return f"{fake.first_name()} {fake.last_name()}"
        if pii_type == "email":
            return f"{fake.user_name()}@example.com"
        if pii_type == "phone":
            if original.strip().startswith("+91"):
                return fake.numerify("+91 1#########")
            if original.strip().startswith("+1") or original.strip().startswith("("):
                return fake.numerify("(415) 555-####")
            return fake.numerify("+91 1#########")
        if pii_type == "company":
            base = re.sub(r",.*$", "", fake.company()).strip()
            base = re.sub(
                r"\s+(Inc\.?|LLC|Ltd\.?|Limited|Corp\.?|Group)$",
                "",
                base,
                flags=re.I,
            ).strip()
            return f"{base} LLC"
        if pii_type == "address":
            return fake.address().replace("\n", ", ")
        if pii_type == "ssn":
            return fake.ssn()
        if pii_type == "credit_card":
            number = fake.credit_card_number(card_type="visa")
            return " ".join(number[i : i + 4] for i in range(0, len(number), 4))
        if pii_type == "date_of_birth":
            dob = fake.date_of_birth(minimum_age=25, maximum_age=70)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", original):
                return dob.strftime("%Y-%m-%d")
            if "/" in original:
                return dob.strftime("%d/%m/%Y")
            return dob.strftime("%d %B %Y")
        if pii_type == "ip_address":
            return f"203.0.113.{fake.random_int(20, 200)}"
        return f"[REDACTED_{pii_type.upper()}]"

    def find(self, text: str) -> list[Finding]:
        raw: list[Finding] = []
        for pii_type, detector in DETECTORS:
            for start, end, value in detector(text):
                raw.append(
                    Finding(
                        pii_type=pii_type,
                        original=value,
                        replacement=self.fake_for(pii_type, value),
                        start=start,
                        end=end,
                    )
                )
        return merge_spans(raw)

    def redact_text(self, text: str) -> tuple[str, list[Finding]]:
        findings = self.find(text)
        redacted = text
        for item in sorted(findings, key=lambda f: f.start, reverse=True):
            redacted = redacted[: item.start] + item.replacement + redacted[item.end :]
        return redacted, findings


def iter_containers(document: Document):
    yield document
    for section in document.sections:
        yield section.header
        yield section.footer


def iter_unique_cells(container):
    seen_ids: set[int] = set()
    keep_alive: list = []
    for table in getattr(container, "tables", []):
        for row in table.rows:
            for cell in row.cells:
                tc = cell._tc
                keep_alive.append(tc)
                marker = id(tc)
                if marker in seen_ids:
                    continue
                seen_ids.add(marker)
                yield cell


def set_paragraph_text(paragraph, text: str) -> None:
    if not paragraph.runs:
        paragraph.add_run(text)
        return
    paragraph.runs[0].text = text
    for run in paragraph.runs[1:]:
        run.text = ""


def extract_docx_text(path: str | Path) -> str:
    document = Document(str(path))
    parts: list[str] = []
    for container in iter_containers(document):
        parts.extend(p.text for p in container.paragraphs)
        parts.extend(cell.text for cell in iter_unique_cells(container))
    return "\n".join(parts)


def redact_docx(input_path: str | Path, output_path: str | Path, redactor: Redactor) -> list[Finding]:
    document = Document(str(input_path))
    all_findings: list[Finding] = []
    for container in iter_containers(document):
        for paragraph in container.paragraphs:
            if not paragraph.text:
                continue
            new_text, findings = redactor.redact_text(paragraph.text)
            if findings:
                set_paragraph_text(paragraph, new_text)
                all_findings.extend(findings)
        for cell in iter_unique_cells(container):
            if not cell.text.strip():
                continue
            new_text, findings = redactor.redact_text(cell.text)
            if findings:
                cell.text = new_text
                all_findings.extend(findings)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return all_findings


def redact_plain_to_docx(text: str, output_path: str | Path, redactor: Redactor) -> list[Finding]:
    new_text, findings = redactor.redact_text(text)
    document = Document()
    for line in new_text.splitlines() or [new_text]:
        document.add_paragraph(line)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Redact PII in a document.")
    parser.add_argument("input", help="Source .docx or .txt file")
    parser.add_argument("-o", "--output", required=True, help="Redacted .docx path")
    parser.add_argument("--log", help="Optional JSON log of replacements")
    parser.add_argument("--preferred", help="JSON map of original -> fake values")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    preferred = dict(DEFAULT_PREFERRED)
    if args.preferred:
        preferred.update(json.loads(Path(args.preferred).read_text()))

    redactor = Redactor(preferred=preferred, seed=args.seed)
    source = Path(args.input)
    if source.suffix.lower() == ".docx":
        findings = redact_docx(source, args.output, redactor)
    else:
        findings = redact_plain_to_docx(source.read_text(encoding="utf-8"), args.output, redactor)

    summary: dict[str, int] = {}
    for item in findings:
        summary[item.pii_type] = summary.get(item.pii_type, 0) + 1
    print(f"Wrote {args.output}")
    print("Replacements:", summary or "none")

    if args.log:
        Path(args.log).parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "output": args.output,
            "counts": summary,
            "replacements": [asdict(item) for item in findings],
        }
        Path(args.log).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
