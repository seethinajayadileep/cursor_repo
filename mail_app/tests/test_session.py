from __future__ import annotations

from fastapi.testclient import TestClient

from mail_app.app import app
from mail_app.sanitize import sanitize_html
from mail_app import store


def test_healthz() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_publisher_domain_association() -> None:
    client = TestClient(app)
    response = client.get("/.well-known/microsoft-identity-association.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    body = response.json()
    assert body["associatedApplications"][0]["applicationId"] == (
        "88fce97a-105c-4085-9e0b-1b9ce3be3080"
    )


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


def test_mailbox_link_works_without_session(monkeypatch) -> None:
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
    client = TestClient(app)
    response = client.get(f"/a/{account.id}")
    assert response.status_code == 200
    assert "Hello" in response.text
    assert "Sign in to manage" in response.text


def test_pending_flow_survives_without_session_cookie() -> None:
    flow = {"state": "st-1", "auth_uri": "https://example.test"}
    store.save_flow("st-1", flow, "test-secret-value-not-for-production")
    loaded = store.pop_flow("st-1", "test-secret-value-not-for-production")
    assert loaded == flow
    assert store.pop_flow("st-1", "test-secret-value-not-for-production") is None


def test_sanitize_strips_script() -> None:
    cleaned = sanitize_html("<p>ok</p><script>alert(1)</script>")
    assert "script" not in cleaned.lower()
    assert "ok" in cleaned


def test_admin_redirects_when_logged_out(monkeypatch) -> None:
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    client = TestClient(app, follow_redirects=False)
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_admin_password_lists_all_mailbox_links(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "openseasame")
    first = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )
    store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="other@example.com",
        email="second@example.com",
        name="Second",
        refresh_token="refresh-token",
    )
    client = TestClient(app, follow_redirects=False)
    locked = client.get("/admin")
    assert locked.status_code == 302
    assert locked.headers["location"] == "/admin/login"

    denied = client.post("/admin/login", data={"password": "wrong"})
    assert denied.status_code == 401
    assert "not correct" in denied.text

    accepted = client.post("/admin/login", data={"password": "openseasame"})
    assert accepted.status_code == 302
    assert accepted.headers["location"] == "/admin"

    page = client.get("/admin")
    assert page.status_code == 200
    assert "pat@example.com" in page.text
    assert "second@example.com" in page.text
    assert f"/a/{first.id}" in page.text
    assert "Copy link" in page.text


def test_signed_in_operator_sees_only_own_admin_rows(monkeypatch) -> None:
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    mine = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )
    store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="other@example.com",
        email="hidden@example.com",
        name="Hidden",
        refresh_token="refresh-token",
    )
    monkeypatch.setattr(
        "mail_app.app._session_user",
        lambda _request: {"name": "Pat", "email": "pat@example.com"},
    )
    monkeypatch.setattr("mail_app.app._owner_email", lambda _request: "pat@example.com")
    client = TestClient(app)
    page = client.get("/admin")
    assert page.status_code == 200
    assert "pat@example.com" in page.text
    assert f"/a/{mine.id}" in page.text
    assert "hidden@example.com" not in page.text


def test_host_session_cannot_bypass_admin_password(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "only-this")
    monkeypatch.setattr(
        "mail_app.app._session_user",
        lambda _request: {"name": "Pat", "email": "pat@example.com"},
    )
    monkeypatch.setattr("mail_app.app._owner_email", lambda _request: "pat@example.com")
    client = TestClient(app, follow_redirects=False)
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"
