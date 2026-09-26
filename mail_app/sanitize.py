from __future__ import annotations

from bleach import clean

try:
    from bleach.css_sanitizer import CSSSanitizer
except ImportError:  # tinycss2 missing; width and height attributes still apply
    CSSSanitizer = None  # type: ignore[misc, assignment]

ALLOWED_TAGS = [
    "a",
    "b",
    "blockquote",
    "br",
    "center",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
]
ALLOWED_ATTRS = {
    "*": [
        "align",
        "bgcolor",
        "border",
        "cellpadding",
        "cellspacing",
        "colspan",
        "height",
        "rowspan",
        "style",
        "valign",
        "width",
    ],
    "a": ["href", "title"],
    "img": ["alt", "height", "src", "title", "width"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}
ALLOWED_CSS = [
    "background-color",
    "border",
    "border-bottom",
    "border-collapse",
    "border-color",
    "border-left",
    "border-radius",
    "border-right",
    "border-spacing",
    "border-style",
    "border-top",
    "border-width",
    "color",
    "display",
    "float",
    "font-family",
    "font-size",
    "font-style",
    "font-weight",
    "height",
    "letter-spacing",
    "line-height",
    "margin",
    "margin-bottom",
    "margin-left",
    "margin-right",
    "margin-top",
    "max-height",
    "max-width",
    "min-width",
    "padding",
    "padding-bottom",
    "padding-left",
    "padding-right",
    "padding-top",
    "text-align",
    "text-decoration",
    "vertical-align",
    "white-space",
    "width",
]
_BLOCKED_STYLE = ("url(", "expression", "javascript", "behavior", "@import", "binding")


class _EmailCSS:
    def __init__(self) -> None:
        self._inner = CSSSanitizer(allowed_css_properties=ALLOWED_CSS) if CSSSanitizer else None

    def sanitize_css(self, style: str) -> str:
        if self._inner is None:
            return ""
        cleaned = self._inner.sanitize_css(style or "")
        kept: list[str] = []
        for part in cleaned.split(";"):
            item = part.strip()
            if not item:
                continue
            lowered = item.lower()
            if any(token in lowered for token in _BLOCKED_STYLE):
                continue
            kept.append(item)
        return "; ".join(kept)


def sanitize_html(html: str) -> str:
    return clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=["http", "https", "mailto", "cid"],
        css_sanitizer=_EmailCSS(),
        strip=True,
    )
