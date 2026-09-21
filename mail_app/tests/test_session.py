from __future__ import annotations

from fastapi.testclient import TestClient

from mail_app.app import app
from mail_app.sanitize import sanitize_html
from mail_app import store


def test_healthz() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "keepalive": False}


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
    assert "Sign out" not in response.text
    assert "Inbox" in response.text
    assert "Sent" in response.text


def test_open_message_shows_reply_and_to_line(monkeypatch) -> None:
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
                "from": {"emailAddress": {"name": "Sam", "address": "sam@example.com"}},
                "receivedDateTime": "2026-01-02T03:04:05Z",
                "bodyPreview": "Hi there",
                "isRead": False,
            }
        ]

    async def fake_get(_token: str, message_id: str) -> dict:
        return {
            "id": message_id,
            "subject": "Hello",
            "from": {"emailAddress": {"name": "Sam", "address": "sam@example.com"}},
            "toRecipients": [{"emailAddress": {"name": "Pat", "address": "pat@example.com"}}],
            "receivedDateTime": "2026-01-02T03:04:05Z",
            "body": {"contentType": "text", "content": "Hi there"},
            "bodyPreview": "Hi there",
            "isRead": False,
        }

    async def fake_read(_token: str, _message_id: str, _is_read: bool) -> None:
        return None

    async def fake_token(_account) -> str:
        return "fake-token"

    monkeypatch.setattr("mail_app.app.graph.list_messages", fake_list)
    monkeypatch.setattr("mail_app.app.graph.get_message", fake_get)
    monkeypatch.setattr("mail_app.app.graph.set_read", fake_read)
    monkeypatch.setattr("mail_app.app._token_for_account", fake_token)
    client = TestClient(app)
    response = client.get(f"/a/{account.id}?msg=msg-1")
    assert response.status_code == 200
    assert "Reply" in response.text
    assert "Forward" in response.text
    assert "To Pat" in response.text
    assert 'id="composer"' in response.text


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
    assert "Connect another mailbox" in response.text
    assert "Sign out" not in response.text
    assert "New message" in response.text
    assert 'id="composer"' in response.text
    assert "Search this folder" in response.text


def test_folder_counts_maps_well_known_names() -> None:
    import asyncio

    async def fake_get(_token: str, path: str, params: dict | None = None) -> dict:
        assert path == "/me/mailFolders"
        return {
            "value": [
                {"wellKnownName": "inbox", "unreadItemCount": 3, "totalItemCount": 80},
                {"displayName": "Sent Items", "unreadItemCount": 0, "totalItemCount": 12},
            ]
        }

    from mail_app import graph

    orig = graph.graph_get
    graph.graph_get = fake_get  # type: ignore[assignment]
    try:
        counts = asyncio.run(graph.folder_counts("token"))
    finally:
        graph.graph_get = orig
    assert counts["inbox"]["unread"] == 3
    assert counts["sentitems"]["total"] == 12


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


def test_delete_and_send_use_graph_write(monkeypatch) -> None:
    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )
    calls: list[tuple] = []

    async def fake_token(_account) -> str:
        return "fake-token"

    async def fake_delete(_token: str, message_id: str) -> None:
        calls.append(("delete", message_id))

    async def fake_send(_token: str, to: str, subject: str, body: str) -> None:
        calls.append(("send", to, subject, body))

    monkeypatch.setattr("mail_app.app._token_for_account", fake_token)
    monkeypatch.setattr("mail_app.app.graph.delete_message", fake_delete)
    monkeypatch.setattr("mail_app.app.graph.send_mail", fake_send)
    client = TestClient(app, follow_redirects=False)
    deleted = client.post(
        f"/a/{account.id}/delete",
        data={"message_id": "msg-1", "folder": "inbox"},
    )
    assert deleted.status_code == 302
    sent = client.post(
        f"/a/{account.id}/send",
        data={"to": "a@example.com", "subject": "Hi", "body": "Hello", "folder": "inbox"},
    )
    assert sent.status_code == 302
    assert sent.headers["location"] == f"/a/{account.id}?folder=sentitems"
    assert calls == [("delete", "msg-1"), ("send", "a@example.com", "Hi", "Hello")]


def test_public_logout_does_not_clear_session() -> None:
    client = TestClient(app, follow_redirects=False)
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_admin_signout_requires_password(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "openseasame")
    client = TestClient(app, follow_redirects=False)
    client.post("/admin/login", data={"password": "openseasame"})
    denied = client.post("/admin/signout", data={"password": "wrong"})
    assert denied.status_code == 401
    assert "Sign out was cancelled" in denied.text
    still = client.get("/admin")
    assert still.status_code == 200
    done = client.post("/admin/signout", data={"password": "openseasame"})
    assert done.status_code == 302
    assert done.headers["location"] == "/admin/login"
    locked = client.get("/admin")
    assert locked.status_code == 302
    assert locked.headers["location"] == "/admin/login"


def test_disconnect_requires_admin_password(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "openseasame")
    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )
    client = TestClient(app, follow_redirects=False)
    blocked = client.post(f"/a/{account.id}/disconnect", data={"password": "openseasame"})
    assert blocked.status_code == 302
    assert blocked.headers["location"] == "/admin/login"
    client.post("/admin/login", data={"password": "openseasame"})
    removed = client.post(f"/a/{account.id}/disconnect", data={"password": "openseasame"})
    assert removed.status_code == 302
    assert removed.headers["location"] == "/admin"
    assert store.get_account(account.id, "test-secret-value-not-for-production") is None


def test_refresh_falls_back_when_write_scopes_are_missing(monkeypatch) -> None:
    from mail_app.auth import refresh_access_token
    from mail_app.config import load_settings

    calls: list[list[str]] = []

    class FakeClient:
        def acquire_token_by_refresh_token(self, _token: str, scopes: list[str]):
            calls.append(list(scopes))
            if "Mail.ReadWrite" in scopes:
                return {"error": "invalid_grant"}
            return {"access_token": "kept-access", "refresh_token": "kept-refresh"}

    monkeypatch.setattr("mail_app.auth.confidential_app", lambda _settings: FakeClient())
    result = refresh_access_token(load_settings(), "old-refresh")
    assert result == {"access_token": "kept-access", "refresh_token": "kept-refresh"}
    assert calls[0] == ["User.Read", "Mail.ReadWrite", "Mail.Send"]
    assert calls[1] == ["User.Read"]


def test_keep_connected_accounts_refreshes_tokens(monkeypatch) -> None:
    import asyncio

    from mail_app.app import keep_connected_accounts

    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="keep@example.com",
        name="Keep",
        refresh_token="old-refresh",
    )

    def fake_refresh(_settings, token: str):
        return {"access_token": "new-access", "refresh_token": f"rotated-{token}"}

    monkeypatch.setattr("mail_app.app.auth.refresh_access_token", fake_refresh)
    kept = asyncio.run(keep_connected_accounts())
    assert kept >= 1
    updated = store.get_account(account.id, "test-secret-value-not-for-production")
    assert updated is not None
    assert updated.refresh_token == "rotated-old-refresh"
