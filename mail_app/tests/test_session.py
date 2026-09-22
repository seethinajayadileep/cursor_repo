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
    assert "Other" in response.text


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
    assert 'id="translate-lang"' in response.text
    assert "Spanish" in response.text
    assert "Show original" in response.text


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


def test_list_messages_puts_newest_first() -> None:
    import asyncio

    from mail_app import graph

    graph._prefer_safe_select = False

    async def fake_get(_token: str, path: str, params: dict | None = None) -> dict:
        assert params is not None
        assert params.get("$orderby") == "receivedDateTime desc"
        assert "inferenceClassification" in (params.get("$select") or "")
        return {
            "value": [
                {
                    "id": "old",
                    "subject": "Older",
                    "receivedDateTime": "2026-09-01T08:00:00Z",
                },
                {
                    "id": "new",
                    "subject": "Newer",
                    "receivedDateTime": "2026-09-21T18:30:00+00:00",
                },
                {
                    "id": "mid",
                    "subject": "Middle",
                    "receivedDateTime": "2026-09-10T12:00:00Z",
                },
            ]
        }

    orig = graph.graph_get
    graph.graph_get = fake_get  # type: ignore[assignment]
    try:
        messages = asyncio.run(graph.list_messages("token"))
    finally:
        graph.graph_get = orig
    assert [item["id"] for item in messages] == ["new", "mid", "old"]


def test_list_incoming_includes_other_and_junk() -> None:
    import asyncio

    from mail_app import graph

    async def fake_get(_token: str, path: str, params: dict | None = None) -> dict:
        if "junkemail" in path:
            return {
                "value": [
                    {
                        "id": "spam",
                        "subject": "Spam",
                        "receivedDateTime": "2026-09-21T19:00:00Z",
                    }
                ]
            }
        if "clutter" in path:
            raise graph.GraphError(404, "no clutter")
        return {
            "value": [
                {
                    "id": "focused",
                    "subject": "Focused",
                    "receivedDateTime": "2026-09-21T12:00:00Z",
                    "inferenceClassification": "focused",
                },
                {
                    "id": "other",
                    "subject": "Other tab",
                    "receivedDateTime": "2026-09-21T13:00:00Z",
                    "inferenceClassification": "other",
                },
            ]
        }

    orig = graph.graph_get
    graph.graph_get = fake_get  # type: ignore[assignment]
    try:
        incoming = asyncio.run(graph.list_incoming_messages("token"))
        others = asyncio.run(graph.list_other_messages("token"))
    finally:
        graph.graph_get = orig
    assert [item["id"] for item in incoming] == ["spam", "other", "focused"]
    assert incoming[0]["_incoming_folder"] == "junkemail"
    assert incoming[1]["_incoming_folder"] == "other"
    assert incoming[2]["_incoming_folder"] == "inbox"
    assert [item["id"] for item in others] == ["other"]


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


def test_sanitize_keeps_email_image_size() -> None:
    cleaned = sanitize_html(
        '<img src="https://cdn.example/logo.png" alt="Logo" width="18" height="18" '
        'style="width:18px;height:18px;display:block;background-image:url(javascript:alert(1))">'
    )
    assert 'src="https://cdn.example/logo.png"' in cleaned
    assert 'width="18"' in cleaned
    assert 'height="18"' in cleaned
    assert "width:18px" in cleaned
    assert "height:18px" in cleaned
    assert "display:block" in cleaned
    assert "javascript" not in cleaned.lower()
    assert "url(" not in cleaned.lower()


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
    assert "admin-row" in page.text
    assert "Mailbox directory" in page.text


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


def test_admin_all_mail_requires_login(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "openseasame")
    client = TestClient(app, follow_redirects=False)
    response = client.get("/admin/inbox")
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"


def test_admin_all_mail_merges_linked_inboxes(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "openseasame")
    first = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="one@example.com",
        name="One",
        refresh_token="refresh-token",
    )
    store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="other@example.com",
        email="two@example.com",
        name="Two",
        refresh_token="refresh-token",
    )

    async def fake_token(account) -> str:
        return account.email

    async def fake_list(token: str, folder: str = "inbox", top: int = 80) -> list[dict]:
        if folder != "inbox":
            return []
        if token == "one@example.com":
            return [
                {
                    "id": "m1",
                    "subject": "Hello one",
                    "from": {"emailAddress": {"name": "Sam", "address": "sam@example.com"}},
                    "receivedDateTime": "2026-09-21T10:00:00Z",
                    "bodyPreview": "First box",
                    "isRead": False,
                }
            ]
        return [
            {
                "id": "m2",
                "subject": "Hello two",
                "from": {"emailAddress": {"name": "Alex", "address": "alex@example.com"}},
                "receivedDateTime": "2026-09-21T11:00:00Z",
                "bodyPreview": "Second box",
                "isRead": True,
            }
        ]

    monkeypatch.setattr("mail_app.app._token_for_account", fake_token)
    monkeypatch.setattr("mail_app.app.graph.list_messages", fake_list)
    client = TestClient(app, follow_redirects=False)
    client.post("/admin/login", data={"password": "openseasame"})
    directory = client.get("/admin")
    assert "All mail" in directory.text
    page = client.get("/admin/inbox")
    assert page.status_code == 200
    assert "Hello two" in page.text
    assert "Hello one" in page.text
    assert page.text.find("Hello two") < page.text.find("Hello one")
    assert "To one@example.com" in page.text
    assert "To two@example.com" in page.text
    assert first.id in page.text
    assert "msg=m1" in page.text
    filtered = client.get(f"/admin/inbox?box={first.id}")
    assert "Hello one" in filtered.text
    assert "Hello two" not in filtered.text
    searched = client.get("/admin/inbox?q=two")
    assert "Hello two" in searched.text
    assert "Hello one" not in searched.text


def test_admin_all_mail_sorts_mixed_timestamps(monkeypatch) -> None:
    import asyncio

    from mail_app.app import collect_linked_inbox

    older = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="older@example.com",
        name="Older",
        refresh_token="refresh-token",
    )
    newer = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="newer@example.com",
        name="Newer",
        refresh_token="refresh-token",
    )

    async def fake_token(account) -> str:
        return account.email

    async def fake_list(token: str, folder: str = "inbox", top: int = 80) -> list[dict]:
        if folder != "inbox":
            return []
        if token == "older@example.com":
            return [
                {
                    "id": "old",
                    "subject": "Old mail",
                    "from": {"emailAddress": {"name": "Sam", "address": "sam@example.com"}},
                    "receivedDateTime": "2026-09-01T08:00:00Z",
                    "bodyPreview": "old",
                    "isRead": True,
                }
            ]
        return [
            {
                "id": "new",
                "subject": "New mail",
                "from": {"emailAddress": {"name": "Alex", "address": "alex@example.com"}},
                "receivedDateTime": "2026-09-21T18:30:00+00:00",
                "bodyPreview": "new",
                "isRead": False,
            }
        ]

    monkeypatch.setattr("mail_app.app._token_for_account", fake_token)
    monkeypatch.setattr("mail_app.app.graph.list_messages", fake_list)
    refs = [ref for ref in store.list_mailbox_refs() if ref.id in {older.id, newer.id}]
    items, skipped = asyncio.run(collect_linked_inbox(refs))
    assert skipped == []
    assert [item.subject for item in items] == ["New mail", "Old mail"]


def test_admin_all_mail_captures_other_and_junk(monkeypatch) -> None:
    import asyncio

    from mail_app.app import collect_linked_inbox

    box = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="mix@example.com",
        name="Mix",
        refresh_token="refresh-token",
    )

    async def fake_token(_account) -> str:
        return "token"

    async def fake_list(_token: str, folder: str = "inbox", top: int = 80) -> list[dict]:
        if folder == "junkemail":
            return [
                {
                    "id": "junk",
                    "subject": "Junk offer",
                    "from": {"emailAddress": {"name": "Spam", "address": "spam@example.com"}},
                    "receivedDateTime": "2026-09-21T20:00:00Z",
                    "bodyPreview": "buy",
                    "isRead": True,
                }
            ]
        if folder == "clutter":
            return []
        return [
            {
                "id": "other",
                "subject": "Other newsletter",
                "from": {"emailAddress": {"name": "News", "address": "news@example.com"}},
                "receivedDateTime": "2026-09-21T19:00:00Z",
                "bodyPreview": "hello",
                "isRead": False,
                "inferenceClassification": "other",
            }
        ]

    monkeypatch.setattr("mail_app.app._token_for_account", fake_token)
    monkeypatch.setattr("mail_app.app.graph.list_messages", fake_list)
    refs = [ref for ref in store.list_mailbox_refs() if ref.id == box.id]
    items, skipped = asyncio.run(collect_linked_inbox(refs))
    assert skipped == []
    assert [item.subject for item in items] == ["Junk offer", "Other newsletter"]
    assert [item.folder for item in items] == ["junkemail", "other"]


def test_other_mailbox_folder_lists_other_mail(monkeypatch) -> None:
    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )

    async def fake_list(_token: str, folder: str = "inbox", top: int = 80) -> list[dict]:
        if folder == "clutter":
            return []
        return [
            {
                "id": "focus",
                "subject": "Focused hello",
                "from": {"emailAddress": {"name": "Sam", "address": "sam@example.com"}},
                "receivedDateTime": "2026-09-21T10:00:00Z",
                "bodyPreview": "hi",
                "isRead": False,
                "inferenceClassification": "focused",
            },
            {
                "id": "other",
                "subject": "Other hello",
                "from": {"emailAddress": {"name": "Alex", "address": "alex@example.com"}},
                "receivedDateTime": "2026-09-21T11:00:00Z",
                "bodyPreview": "hey",
                "isRead": False,
                "inferenceClassification": "other",
            },
        ]

    async def fake_token(_account) -> str:
        return "fake-token"

    monkeypatch.setattr("mail_app.app.graph.list_messages", fake_list)
    monkeypatch.setattr("mail_app.app._token_for_account", fake_token)
    client = TestClient(app)
    page = client.get(f"/a/{account.id}?folder=other")
    assert page.status_code == 200
    assert "Other hello" in page.text
    assert "Focused hello" not in page.text
    assert "folder=other" in page.text


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


def test_reconnect_keeps_the_same_mailbox_link() -> None:
    first = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="same@example.com",
        name="Pat",
        refresh_token="first-token",
    )
    again = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="same@example.com",
        name="Patricia",
        refresh_token="second-token",
    )
    assert again.id == first.id
    assert again.created_at == first.created_at
    assert again.refresh_token == "second-token"
    assert again.name == "Patricia"


def test_backup_copies_saved_mailboxes() -> None:
    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="backup@example.com",
        name="Backup",
        refresh_token="refresh-token",
    )
    copied = store.backup_database()
    assert copied is not None
    assert copied.exists()
    saved = store.get_account(account.id, "test-secret-value-not-for-production")
    assert saved is not None
    assert saved.email == "backup@example.com"


def test_locked_mailbox_stays_in_the_database() -> None:
    import sqlite3

    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="locked@example.com",
        name="Locked",
        refresh_token="refresh-token",
    )
    with sqlite3.connect(store.db_path()) as conn:
        conn.execute(
            "UPDATE accounts SET refresh_token = ? WHERE id = ?",
            ("not-a-fernet-token", account.id),
        )
        conn.commit()
    client = TestClient(app)
    page = client.get(f"/a/{account.id}")
    assert page.status_code == 503
    assert "still saved" in page.text
    assert account.id in page.text
    assert store.get_mailbox_ref(account.id) is not None


def test_keepalive_skips_a_locked_row(monkeypatch) -> None:
    import asyncio
    import sqlite3

    from mail_app.app import keep_connected_accounts

    good = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="kept-good@example.com",
        name="Good",
        refresh_token="good-refresh",
    )
    locked = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="kept-locked@example.com",
        name="Locked",
        refresh_token="locked-refresh",
    )
    with sqlite3.connect(store.db_path()) as conn:
        conn.execute(
            "UPDATE accounts SET refresh_token = ? WHERE id = ?",
            ("not-a-fernet-token", locked.id),
        )
        conn.commit()

    def fake_refresh(_settings, token: str):
        return {"access_token": "new-access", "refresh_token": f"rotated-{token}"}

    monkeypatch.setattr("mail_app.app.auth.refresh_access_token", fake_refresh)
    kept = asyncio.run(keep_connected_accounts())
    assert kept >= 1
    updated = store.get_account(good.id, "test-secret-value-not-for-production")
    assert updated is not None
    assert updated.refresh_token == "rotated-good-refresh"
    assert store.get_mailbox_ref(locked.id) is not None


def test_mailbox_access_token_is_reused(monkeypatch) -> None:
    import asyncio

    from mail_app.app import _token_cache, _token_for_account

    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="cached-token@example.com",
        name="Cached",
        refresh_token="cache-refresh",
    )
    _token_cache.pop(account.id, None)
    calls: list[str] = []

    def fake_refresh(_settings, token: str):
        calls.append(token)
        return {"access_token": "cached-access", "refresh_token": token}

    async def twice():
        first = await _token_for_account(account)
        second = await _token_for_account(account)
        return first, second

    monkeypatch.setattr("mail_app.app.auth.refresh_access_token", fake_refresh)
    first, second = asyncio.run(twice())
    assert first == second == "cached-access"
    assert calls == ["cache-refresh"]


def test_list_messages_retries_without_other_field() -> None:
    import asyncio

    from mail_app import graph

    graph._prefer_safe_select = False
    calls: list[str] = []

    async def fake_get(_token: str, path: str, params: dict | None = None) -> dict:
        select = (params or {}).get("$select") or ""
        calls.append(select)
        if "inferenceClassification" in select:
            raise graph.GraphError(400, "unsupported select")
        return {
            "value": [
                {
                    "id": "kept",
                    "subject": "Kept",
                    "receivedDateTime": "2026-09-21T12:00:00Z",
                }
            ]
        }

    orig = graph.graph_get
    graph.graph_get = fake_get  # type: ignore[assignment]
    try:
        messages = asyncio.run(graph.list_messages("token"))
    finally:
        graph.graph_get = orig
    assert [item["id"] for item in messages] == ["kept"]
    assert any("inferenceClassification" in select for select in calls)
    assert any("inferenceClassification" not in select for select in calls)


def test_translate_unknown_mailbox() -> None:
    client = TestClient(app)
    response = client.post(
        "/a/missing-box/translate",
        json={"subject": "Hi", "body": "Hello", "target": "es"},
    )
    assert response.status_code == 404


def test_translate_rejects_unknown_language() -> None:
    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )
    client = TestClient(app)
    response = client.post(
        f"/a/{account.id}/translate",
        json={"subject": "Hi", "body": "Hello", "target": "xx"},
    )
    assert response.status_code == 502
    assert response.json()["error"] == "Translation failed"


def test_translate_returns_subject_and_body(monkeypatch) -> None:
    account = store.upsert_account(
        secret="test-secret-value-not-for-production",
        owner_email="pat@example.com",
        email="pat@example.com",
        name="Pat",
        refresh_token="refresh-token",
    )

    async def fake_pair(subject: str, body: str, target: str) -> tuple[str, str]:
        assert subject == "Hello"
        assert body == "Hi there"
        assert target == "es"
        return "Hola", "Cuerpo"

    async def should_not_refresh(_account):
        raise AssertionError("translate must not refresh mailbox tokens")

    monkeypatch.setattr("mail_app.app.translate_pair", fake_pair)
    monkeypatch.setattr("mail_app.app._token_for_account", should_not_refresh)
    client = TestClient(app)
    response = client.post(
        f"/a/{account.id}/translate",
        json={"subject": "Hello", "body": "Hi there", "target": "es"},
    )
    assert response.status_code == 200
    assert response.json() == {"subject": "Hola", "body": "Cuerpo", "target": "es"}


def test_translate_chunks_keep_every_character() -> None:
    from mail_app.translate import _chunks

    text = ("line one\n" * 40) + ("word " * 200)
    assert "".join(_chunks(text, limit=420)) == text
    assert "".join(_chunks("short", limit=420)) == "short"


def test_mymemory_warning_is_rejected(monkeypatch) -> None:
    import asyncio

    import httpx

    from mail_app.translate import TranslateError, translate_pair

    monkeypatch.delenv("AZURE_TRANSLATOR_KEY", raising=False)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "responseStatus": 200,
                "responseData": {
                    "translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS"
                },
            },
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("mail_app.translate.httpx.AsyncClient", fake_client)
    try:
        asyncio.run(translate_pair("Hello", "Body", "es"))
    except TranslateError:
        return
    raise AssertionError("expected TranslateError")
