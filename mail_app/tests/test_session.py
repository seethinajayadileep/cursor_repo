from __future__ import annotations

from fastapi.testclient import TestClient

from mail_app.app import app
from mail_app.sanitize import sanitize_html
from mail_app import store


def test_inbox_requires_session() -> None:
    client = TestClient(app, follow_redirects=False)
    response = client.get("/inbox")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_unique_mailbox_url_requires_session() -> None:
    client = TestClient(app, follow_redirects=False)
    response = client.get("/a/not-a-real-id")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_message_requires_session() -> None:
    client = TestClient(app, follow_redirects=False)
    response = client.get("/mail/AAMk-example-id")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_signed_in_unique_inbox(monkeypatch) -> None:
    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )

    async def fake_list(_token: str, folder: str = "inbox", top: int = 80) -> list[dict]:
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

    async def fake_token(_account) -> str:
        return "fake-token"

    monkeypatch.setattr("mail_app.app.graph.list_messages", fake_list)
    monkeypatch.setattr("mail_app.app._token_for_account", fake_token)
    monkeypatch.setattr(
        "mail_app.app._session_user",
        lambda _request: {"name": "Pat", "email": "pat@example.com"},
    )
    monkeypatch.setattr("mail_app.app._owner_email", lambda _request: "pat@example.com")
    monkeypatch.setattr("mail_app.app._can_open", lambda _request, _account: True)

    client = TestClient(app)
    response = client.get(f"/a/{account.id}")
    assert response.status_code == 200
    assert "Hello" in response.text
    assert "pat@example.com" in response.text
    assert account.id in response.text


def test_sanitize_strips_script() -> None:
    cleaned = sanitize_html("<p>ok</p><script>alert(1)</script>")
    assert "script" not in cleaned.lower()
    assert "ok" in cleaned
