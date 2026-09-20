# Private Outlook inbox (Microsoft OAuth)

Web app that signs **you** in with Microsoft and shows **your** mailboxes. Each connected account gets a unique host URL such as `https://your-domain/a/<id>`. Opening that URL still requires being signed in to this website. It is not a public share link.

## What it does

1. **Sign in with Microsoft** (OAuth). No app-stored Outlook passwords.
2. After a successful connect, the mailbox is saved (encrypted refresh token) and gets a unique ID.
3. **Connect another account** to add more mailboxes under the same signed-in operator.
4. Later visits: sign in to the host once, then open `/a/<id>` without repeating Microsoft consent (until Microsoft revokes the refresh token).
5. Large three-pane UI: mailboxes / folder list / reading pane.

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
export PUBLIC_BASE_URL=http://localhost:8001
export REDIRECT_URI=http://localhost:8001/auth/callback
export SESSION_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
uvicorn mail_app.app:app --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001` and sign in.

Use HTTPS and `https_only` cookies in production. Never put `AZURE_CLIENT_SECRET` in the repo.

## AADSTS50020 (personal Outlook cannot sign in)

Error text like: account `@outlook.com` from `live.com` does not exist in tenant `Default Directory`.

**Cause:** login is going to *your company tenant* (`AZURE_TENANT_ID=<Directory ID>`). Hotmail/Outlook personal accounts live on `live.com`, not in that directory.

**Fix:**

1. Set `AZURE_TENANT_ID=common` (or `consumers` if you only want personal Microsoft accounts). Do **not** use the Directory (tenant) GUID for `@outlook.com` sign-in.
2. In Entra → your app → **Authentication** (or the app **Manifest**): supported accounts must be **Accounts in any organizational directory and personal Microsoft accounts**. Manifest: `"signInAudience": "AzureADandPersonalMicrosoftAccount"`.
3. Sign out of Microsoft in the browser, then sign in again.

Do not add the Outlook user as a guest in Default Directory unless you only want work accounts.

## Deploy to your host

1. Put the app on Render, Railway, Fly, or any Docker host using the repo `Dockerfile` / `Procfile`.
2. Set env vars: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID=common`, `SESSION_SECRET` (long random), `PUBLIC_BASE_URL=https://your-domain`, `REDIRECT_URI=https://your-domain/auth/callback`, `HTTPS_ONLY=1`.
3. In Entra add the production redirect URI: `https://your-domain/auth/callback` (Web).
4. Open `https://your-domain`, sign in, then use **Connect another account** for each mailbox. Copy the unique `/a/<id>` URL from the left pane.

Keep `SESSION_SECRET` stable after the first deploy. Changing it invalidates stored mailbox tokens.

## Tests

```bash
pip install pytest
pytest mail_app/tests -q
```
