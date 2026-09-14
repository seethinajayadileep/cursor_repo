from __future__ import annotations

import re
from difflib import SequenceMatcher

from openscout.models import Action, Element, Snapshot

SKIP_HREFS = ("mailto:", "tel:", "javascript:")
SKIP_NAMES = {"logout", "log out", "sign out", "delete account"}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _score_field(query: str, value: str) -> float:
    q = normalize(query)
    n = normalize(value)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0
    if n.startswith(q) or q.startswith(n):
        return 0.95
    if q in n or n in q:
        return 0.9
    return SequenceMatcher(None, q, n).ratio()


def score_element(query: str, element: Element, action_type: str) -> float:
    fields = [
        element.label,
        element.aria,
        element.text,
        element.placeholder,
        element.name,
        element.testid,
        element.href,
    ]
    best = max((_score_field(query, field) for field in fields), default=0.0)

    if action_type == "click":
        if element.tag in {"button", "a", "summary"} or element.role in {"button", "link", "tab"}:
            best += 0.04
        if element.type in {"submit", "button"}:
            best += 0.03
        if element.tag in {"input", "textarea", "select"} and element.type not in {"submit", "button"}:
            best -= 0.25
    elif action_type == "fill":
        if element.tag in {"input", "textarea"}:
            best += 0.08
        elif element.tag == "select":
            best += 0.04
        else:
            best -= 0.3
        if query.lower() in {"email", "e-mail"} and element.type == "email":
            best += 0.15
    elif action_type == "select":
        if element.tag == "select":
            best += 0.2
        else:
            best -= 0.2
    elif action_type in {"check", "uncheck"}:
        if element.type in {"checkbox", "radio"}:
            best += 0.2
        else:
            best -= 0.2

    if element.disabled:
        best -= 0.5
    return best


def find_element(
    snapshot: Snapshot,
    query: str,
    action_type: str,
    threshold: float = 0.58,
) -> Element | None:
    ranked = sorted(
        snapshot.elements,
        key=lambda el: score_element(query, el, action_type),
        reverse=True,
    )
    if not ranked:
        return None
    best = ranked[0]
    if score_element(query, best, action_type) < threshold:
        return None
    return best


def suggest_locator(action: Action, element: Element | None) -> str | None:
    if element is None:
        if action.type == "open":
            return f'page.goto("{action.target}")'
        return None
    name = (element.accessible_name or action.target).replace('"', '\\"')
    if action.type == "click":
        role = "button" if element.tag in {"button", "input", "summary"} or element.role == "button" else "link"
        if element.tag == "a" or element.role == "link":
            role = "link"
        return f'page.get_by_role("{role}", name="{name}")'
    if action.type == "fill":
        label = (element.label or element.placeholder or element.name or action.target).replace('"', '\\"')
        return f'page.get_by_label("{label}")'
    if action.type == "select":
        return f'page.get_by_label("{name}").select_option("{action.value}")'
    return f'page.locator("[data-openscout-id=\\"{element.id}\\"]")'


def is_skippable(element: Element) -> bool:
    name = normalize(element.accessible_name)
    if name in SKIP_NAMES:
        return True
    href = (element.href or "").lower()
    return href.startswith(SKIP_HREFS)


def fill_value_for(element: Element) -> str:
    kind = (element.type or "").lower()
    name = normalize(element.accessible_name + " " + element.name + " " + element.placeholder)
    if kind == "email" or "email" in name:
        return "ada@example.com"
    if kind == "password" or "password" in name:
        return "ScoutTest!234"
    if kind in {"tel", "phone"} or "phone" in name:
        return "5550100"
    if kind in {"number", "range"} or "qty" in name or "quantity" in name:
        return "2"
    if "coupon" in name or "promo" in name:
        return "SAVE50"
    if "name" in name:
        return "Ada Lovelace"
    if "city" in name:
        return "Lisbon"
    if "note" in name or "message" in name or "comment" in name:
        return "Please leave at the kiln door."
    return "Scout Tester"
