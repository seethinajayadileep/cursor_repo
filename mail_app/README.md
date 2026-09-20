# Private Outlook inbox (Microsoft OAuth)

Web app that signs **you** in with Microsoft and shows **only your** Inbox. Mail is loaded with Microsoft Graph. Access is a private session cookie — not a public `/inbox/randomid` share link.

## What it does

1. **Sign in with Microsoft** (OAuth). No app-stored Outlook passwords.
2. Session cookie holds your tokens for this browser only.
3. `/inbox` lists your Inbox.
4. `/mail/<graph-message-id>` opens one message **if you are still signed in**. The same URL is useless in another browser.

## Azure app registration

1. Open [Microsoft Entra admin center](https://entra.microsoft.com) → **App registrations** → **New registration**.
2. Name: `Private Outlook Inbox`.
3. Supported accounts: **Accounts in any organizational directory and personal Microsoft accounts**.
4. Redirect URI: **Web** → `http://localhost:8001/auth/callback` (add your HTTPS URL in production).
5. Create a **client secret** and copy the value.
6. **API permissions**: Microsoft Graph delegated `User.Read` and `Mail.Read`. Grant admin consent if your tenant requires it.

## Run

From the repo root (needs the root `requirements.txt` packages plus `mail_app/requirements.txt`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r mail_app/requirements.txt
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export AZURE_TENANT_ID=common
export REDIRECT_URI=http://localhost:8001/auth/callback
export SESSION_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
uvicorn mail_app.app:app --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001` and sign in.

Use HTTPS and `https_only` cookies in production. Never put `AZURE_CLIENT_SECRET` in the repo.

## Tests

```bash
pip install pytest
pytest mail_app/tests -q
```
