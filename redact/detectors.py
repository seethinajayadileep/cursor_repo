"""Find PII spans in cleaned text.

Each detector returns a list of dicts:
    {"start": int, "end": int, "text": str, "type": str}

Structured types (email, phone, SSN, card, IP, DOB) use regex.
Names, companies, and addresses use a gazetteer plus conservative patterns.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

GAZETTEER_PATH = Path(__file__).resolve().parent.parent / "data" / "gazetteer.json"

PII_TYPES = (
    "name",
    "email",
    "phone",
    "company",
    "address",
    "ssn",
    "credit_card",
    "dob",
    "ip",
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Indian mobiles, landlines, and +91 numbers. Avoids rupee amounts and years.
PHONE_RE = re.compile(
    r"""
    (?:
        \+?\s*91(?:[\s\-]*\d{2,5}){2,4}         # +91 20 4505 3237 / +91 81081 14949
        |
        \b[6-9]\d{9}\b                          # 10-digit mobile
    )
    """,
    re.VERBOSE,
)

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# 13–19 digits, optional spaces/dashes, validated with Luhn later.
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")

IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\b"
)
IPV6_RE = re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b")

DOB_RE = re.compile(
    r"(?:date\s+of\s+birth|d\.?o\.?b\.?|born(?:\s+on)?)\s*[:\-]?\s*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)

# Legal-entity suffix: "Foo Bar Private Limited", "Foo LLP"
COMPANY_SUFFIX_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.'’\-]+(?:\s+[A-Z0-9][A-Za-z0-9&.'’\-]*){0,8})"
    r"(?:\s+(?:Private|Pvt\.?))?"
    r"\s+(?:Limited|Ltd\.?|LLP|Corporation|Inc\.?)\b"
)

FAMILY_TRUST_RE = re.compile(
    r"\b[A-Z][A-Za-z]+\s+Family\s+Trust\b",
    re.IGNORECASE,
)

CONTACT_PERSON_RE = re.compile(
    r"Contact\s+Person:\s*([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3}"
    r"(?:\s*/\s*[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3})?)",
)

# Company-like phrases we do not want to treat as PII.
COMPANY_DENY = {
    "companies act",
    "limited liability",
    "the company",
    "our company",
    "public limited company",
    "private limited company",
    "equity shares of face value",
}

# Suffix-regex hits that swallow heading words ("Book Built Offer KSH ... Limited").
COMPANY_STOPWORDS = {
    "offer",
    "prospectus",
    "act",
    "regulation",
    "regulations",
    "section",
    "dated",
    "page",
    "equity",
    "share",
    "shares",
    "issue",
    "fresh",
    "board",
    "built",
}

# Tokens that are not a person even if Title Cased.
NAME_DENY = {
    "red herring",
    "offer price",
    "fresh issue",
    "equity shares",
    "book built",
    "contact person",
    "company secretary",
    "compliance officer",
    "registered office",
    "corporate office",
    "managing director",
    "executive director",
    "independent director",
    "statutory auditors",
    "lead managers",
    "care report",
    "fiscal year",
    "india limited",  # leftover of a longer company name
}


@lru_cache(maxsize=1)
def load_gazetteer() -> dict:
    with GAZETTEER_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _span(start: int, end: int, text: str, pii_type: str) -> dict:
    return {"start": start, "end": end, "text": text[start:end], "type": pii_type}


def _find_literal(text: str, needle: str, pii_type: str) -> list[dict]:
    if not needle.strip():
        return []
    spans = []
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    for match in pattern.finditer(text):
        spans.append(_span(match.start(), match.end(), text, pii_type))
    return spans


def detect_emails(text: str) -> list[dict]:
    return [_span(m.start(), m.end(), text, "email") for m in EMAIL_RE.finditer(text)]


def detect_phones(text: str) -> list[dict]:
    spans = []
    for match in PHONE_RE.finditer(text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        # Drop short / CIN-like leftovers. Indian numbers are 10–12 digits with 91.
        if len(digits) < 10 or len(digits) > 13:
            continue
        spans.append(_span(match.start(), match.end(), text, "phone"))
    return spans


def detect_ssn(text: str) -> list[dict]:
    return [_span(m.start(), m.end(), text, "ssn") for m in SSN_RE.finditer(text)]


def _luhn_ok(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def detect_credit_cards(text: str) -> list[dict]:
    spans = []
    for match in CARD_RE.finditer(text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        # Skip years, share counts, rupee figures without card length + Luhn.
        if _luhn_ok(digits):
            spans.append(_span(match.start(), match.end(), text, "credit_card"))
    return spans


def detect_ips(text: str) -> list[dict]:
    spans = [_span(m.start(), m.end(), text, "ip") for m in IPV4_RE.finditer(text)]
    spans += [_span(m.start(), m.end(), text, "ip") for m in IPV6_RE.finditer(text)]
    return spans


def detect_dobs(text: str) -> list[dict]:
    spans = []
    for match in DOB_RE.finditer(text):
        spans.append(_span(match.start(1), match.end(1), text, "dob"))
    return spans


def detect_names(text: str) -> list[dict]:
    gaz = load_gazetteer()
    # Longer names first so "Rajesh Kushal Hegde" wins over "Rajesh Hegde".
    people = sorted(gaz["people"], key=len, reverse=True)
    spans: list[dict] = []
    for name in people:
        if name.lower() in NAME_DENY:
            continue
        spans.extend(_find_literal(text, name, "name"))
    for match in CONTACT_PERSON_RE.finditer(text):
        value = match.group(1)
        # Split "Lokesh Shah/ Soumavo Sarkar"
        for part in re.split(r"\s*/\s*", value):
            part = part.strip()
            if len(part.split()) >= 2 and part.lower() not in NAME_DENY:
                start = text.find(part, match.start(1), match.end(1))
                if start >= 0:
                    spans.append(_span(start, start + len(part), text, "name"))
    return spans


def detect_companies(text: str) -> list[dict]:
    gaz = load_gazetteer()
    companies = sorted(gaz["companies"], key=len, reverse=True)
    spans: list[dict] = []
    for name in companies:
        if name.lower() in COMPANY_DENY:
            continue
        spans.extend(_find_literal(text, name, "company"))
    for regex in (COMPANY_SUFFIX_RE, FAMILY_TRUST_RE):
        for match in regex.finditer(text):
            value = match.group(0).strip()
            lowered = value.lower()
            if lowered in COMPANY_DENY:
                continue
            tokens = set(re.findall(r"[a-z]+", lowered))
            if tokens & COMPANY_STOPWORDS:
                continue
            if lowered.startswith("the ") and "limited" not in lowered:
                continue
            spans.append(_span(match.start(), match.end(), text, "company"))
    return spans


def detect_addresses(text: str) -> list[dict]:
    gaz = load_gazetteer()
    addresses = sorted(gaz["addresses"], key=len, reverse=True)
    spans: list[dict] = []
    for addr in addresses:
        # Gazetteer addresses may differ slightly in punctuation after cleaning.
        compact = " ".join(addr.split())
        spans.extend(_find_literal(text, compact, "address"))
        # Also try an en-dash / hyphen variant.
        spans.extend(_find_literal(text, compact.replace("–", "-"), "address"))
        spans.extend(_find_literal(text, compact.replace("-", "–"), "address"))

    # PIN-code anchored Indian address (6 digits, often written as 410 501).
    pin_re = re.compile(
        r"(?:Plot\s+No\.?|Village|Tower|Wing|Floor|House|Marg|Road|Complex|"
        r"\d{1,4}/\d{1,4})[\w\s,./–\-()]{10,160}?"
        r"(?:Maharashtra|Mumbai|Pune|India)"
        r"(?:,?\s*India)?"
        r"(?:,?\s*\d{3}\s?\d{3})?",
        re.IGNORECASE,
    )
    for match in pin_re.finditer(text):
        value = match.group(0).strip()
        if len(value) < 20:
            continue
        spans.append(_span(match.start(), match.end(), text, "address"))
    street_re = re.compile(
        r"\b\d{1,5}\s+[A-Za-z][A-Za-z .]{1,40}(?:Road|Marg|Street|Nagar|Lane)"
        r"[\w\s,./–\-()]{0,80}\d{3}\s?\d{3}"
        r"(?:,?\s*Maharashtra)?(?:,?\s*India)?",
        re.IGNORECASE,
    )
    for match in street_re.finditer(text):
        value = match.group(0).strip()
        if len(value) < 16:
            continue
        spans.append(_span(match.start(), match.end(), text, "address"))
    return spans


DETECTORS = (
    detect_emails,
    detect_phones,
    detect_ssn,
    detect_credit_cards,
    detect_ips,
    detect_dobs,
    detect_names,
    detect_companies,
    detect_addresses,
)


def detect_all(text: str) -> list[dict]:
    """Run every detector and return unsorted, possibly overlapping spans."""
    spans: list[dict] = []
    for detector in DETECTORS:
        spans.extend(detector(text))
    return spans
