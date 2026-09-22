from __future__ import annotations

import os

import httpx

TRANSLATE_LANGS: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("pt", "Portuguese"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("hi", "Hindi"),
    ("vi", "Vietnamese"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("ar", "Arabic"),
    ("ru", "Russian"),
    ("tr", "Turkish"),
    ("nl", "Dutch"),
)
_LANG_CODES = {code for code, _label in TRANSLATE_LANGS}
_AZURE_CODES = {"zh": "zh-Hans"}
_MYMEMORY_CODES = {"zh": "zh-CN"}
_CHUNK = 420


class TranslateError(RuntimeError):
    pass


def language_label(code: str) -> str:
    for key, label in TRANSLATE_LANGS:
        if key == code:
            return label
    return code


def _chunks(text: str, limit: int = _CHUNK) -> list[str]:
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            split = text.rfind("\n", start, end)
            if split > start:
                end = split + 1
        piece = text[start:end]
        if not piece:
            break
        pieces.append(piece)
        start = end
    return pieces or [text]


async def translate_pair(subject: str, body: str, target: str) -> tuple[str, str]:
    if target not in _LANG_CODES:
        raise TranslateError("unsupported language")
    subject = (subject or "").strip()[:300]
    body = (body or "").strip()[:8000]
    if not subject and not body:
        return "", ""
    if os.getenv("AZURE_TRANSLATOR_KEY", "").strip():
        return await _azure(subject, body, target)
    return await _mymemory(subject, body, target)


async def _azure(subject: str, body: str, target: str) -> tuple[str, str]:
    key = os.getenv("AZURE_TRANSLATOR_KEY", "").strip()
    region = os.getenv("AZURE_TRANSLATOR_REGION", "eastus").strip() or "eastus"
    payload = [{"text": subject}, {"text": body}]
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.cognitive.microsofttranslator.com/translate",
            params={"api-version": "3.0", "to": _AZURE_CODES.get(target, target)},
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Ocp-Apim-Subscription-Region": region,
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if response.status_code >= 400:
        raise TranslateError("translator rejected the request")
    data = response.json()
    try:
        translated_subject = data[0]["translations"][0]["text"]
        translated_body = data[1]["translations"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TranslateError("translator returned an unexpected response") from exc
    return translated_subject, translated_body


async def _mymemory(subject: str, body: str, target: str) -> tuple[str, str]:
    code = _MYMEMORY_CODES.get(target, target)

    async def one(text: str, client: httpx.AsyncClient) -> str:
        if not text.strip():
            return ""
        parts: list[str] = []
        for chunk in _chunks(text):
            response = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": chunk, "langpair": f"Autodetect|{code}"},
            )
            if response.status_code >= 400:
                raise TranslateError("translator rejected the request")
            data = response.json()
            translated = ((data.get("responseData") or {}).get("translatedText") or "").strip()
            status = data.get("responseStatus")
            if status not in (200, "200") or not translated or translated.upper().startswith("MYMEMORY"):
                raise TranslateError("translator returned an unexpected response")
            parts.append(translated)
        return "".join(parts).strip()

    async with httpx.AsyncClient(timeout=20.0) as client:
        return await one(subject, client), await one(body, client)
