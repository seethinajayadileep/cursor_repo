# Private Outlook inbox (Microsoft OAuth)

Web app that signs **you** in with Microsoft and shows **your** mailboxes. Each connected account gets a unique host URL such as `https://your-domain/a/<id>`. Open that link on a new device to see that inbox without connecting Microsoft again. Keep the link private. The home page does not list all mailboxes.

## What it does

1. **Sign in with Microsoft** (OAuth). No app-stored Outlook passwords.
2. After a successful connect, the mailbox is saved (encrypted refresh token) and gets a unique ID.
3. **Connect another account** to add more mailboxes under the same signed-in operator.
4. Later visits / new device: open `https://your-domain/a/<id>` to see that mailbox. Microsoft consent is not required again until the token is revoked.
5. Mailbox UI: folders, search, reading pane, reply/forward, and a compose window. Sign in on `/` only to connect or list all of *your* boxes.

## Azure app registration

1. Open [Microsoft Entra admin center](https://entra.microsoft.com) → **App registrations** → **New registration**.
2. Name: `Private Outlook Inbox`.
3. Supported accounts: **Accounts in any organizational directory and personal Microsoft accounts**.
4. Redirect URI: **Web** → `http://localhost:8001/auth/callback` (add your HTTPS URL in production).
5. To verify a **publisher domain**, Entra looks for `/.well-known/microsoft-identity-association.json`. This app serves that file. DNS for the custom domain must already point at the deployed app before you click **Verify and save domain**.
6. Create a **client secret** and copy the value.
7. **API permissions**: Microsoft Graph delegated `User.Read`, `Mail.ReadWrite`, and `Mail.Send`. After you add write/send, reconnect each mailbox so Microsoft shows the new consent.

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

## Deploy (Railway recommended)

1. Create a Railway project from this repo. Attach a **volume** at `/data`.
2. Set env vars (do not change `SESSION_SECRET` later):

```
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=common
SESSION_SECRET=          # long random, generate once
ADMIN_PASSWORD=          # required to open /admin for every mailbox
PUBLIC_BASE_URL=https://your-app.up.railway.app
REDIRECT_URI=https://your-app.up.railway.app/auth/callback
HTTPS_ONLY=1
MAIL_DB_PATH=/data/accounts.sqlite
```

3. Entra → app → Authentication → add Web redirect `https://your-app.up.railway.app/auth/callback`.
4. Health check: `GET /healthz`.

Render: use `render.yaml`, paid instance, **persistent disk** at `/data`, same env vars. Do not use a sleeping free web service.

Keep `SESSION_SECRET` stable after the first deploy. Changing it invalidates stored mailbox tokens.

## How long a connected account stays

The mailbox stays connected **until they revoke it** (Microsoft account → apps that can access your data → remove this app), or until an admin disconnects it here with the admin password.

Connecting the same address again keeps the same `/a/<id>` link. The database uses SQLite WAL with full sync, and each process start writes `accounts.sqlite.bak` next to the live file. A changed `SESSION_SECRET` does not delete rows; the link stays and asks you to restore the original secret.

The site refreshes Microsoft tokens in the background about every 6 hours so the link does not die from sitting unused. Also keep `SESSION_SECRET` unchanged.

## Admin directory

`/admin` lists mailbox addresses and their private `/a/<id>` access links.

- Set `ADMIN_PASSWORD` in Railway. Then open `/admin`, enter that password, and you see **every** connected mailbox.
- If `ADMIN_PASSWORD` is not set, only a Microsoft-signed-in operator can open `/admin`, and only **their** mailboxes are listed.
- Unique mailbox links (`/a/<id>`) never unlock this page. Wrong passwords do not reveal whether a mailbox exists.
- `/admin/inbox` shows incoming mail from **all linked mailboxes** (Inbox, Outlook Other, and Junk) in one list. Open a row to read it on the same page. Each unique mailbox link also has Inbox, Other, Sent, Drafts, Junk, and Deleted.

## Tests

```bash
pip install pytest
pytest mail_app/tests -q
```
