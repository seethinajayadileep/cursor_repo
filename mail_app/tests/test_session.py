from __future__ import annotations

from fastapi.testclient import TestClient

from mail_app.app import app
from mail_app.sanitize import sanitize_html


def test_inbox_requires_session() -> None:
    client = TestClient(app, follow_redirects=False)
    response = client.get("/inbox")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_message_requires_session() -> None:
    client = TestClient(app, follow_redirects=False)
    response = client.get("/mail/AAMk-example-id")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_signed_in_inbox_lists_only_session_messages(monkeypatch) -> None:
    async def fake_list(_token: str, top: int = 50) -> list[dict]:
        return [
            {
                "id": "msg-1",
                "subject": "Hello",
                "from": {"emailAddress": {"name": "Pat", "address": "pat@example.com"}},
                "receivedDateTime": "2026-01-02T03:04:05Z",
                "bodyPreview": "Hi there",
                "isRead": False,
            }
        ]

    monkeypatch.setattr("mail_app.app.graph.list_inbox", fake_list)
    monkeypatch.setattr(
        "mail_app.app._session_user",
        lambda _request: {"name": "Pat", "email": "pat@example.com"},
    )

    async def fake_token(_request):
        return "fake-token"

    monkeypatch.setattr("mail_app.app._access_token", fake_token)
    client = TestClient(app)

    response = client.get("/inbox")
    assert response.status_code == 200
    assert "Hello" in response.text
    assert "pat@example.com" in response.text
    assert "/mail/msg-1" in response.text


def test_sanitize_strips_script() -> None:
    cleaned = sanitize_html('<p>ok</p><script>alert(1)</script>')
    assert "script" not in cleaned.lower()
    assert "ok" in cleaned
