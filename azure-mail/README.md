# Azure mail fix (credit subscriptions)

Azure **cannot** send mail on port 25 when you are on credits / sponsorship / most personal subscriptions. Microsoft will not flip that switch.

This folder is the working setup:

| Direction | How |
|---|---|
| **Receive** | Azure VM + Mailcow, inbound TCP 25, your MX records |
| **Send** | Azure Communication Services SMTP `smtp.azurecomm.net:587` (paid from the same credit) |
| **Admin** | Mailcow web UI — add every domain, mailbox, catch-all |

That is the Azure equivalent of a Hostinger mail VPS. Do not install Mailcow alone and expect Gmail delivery; outbound 25 is dropped at the Azure platform.

## Cost (uses the $1000 credit)

- VM `Standard_B2ms` (2 vCPU, 8 GB) + 128 GB disk + public IP: about **$50–80 / month**
- ACS Email: about **$0.00025 per message**
- **$1000 lasts roughly 12–18 months** if the VM stays the size above

No per-mailbox fee. Extra domains are free on this VM.

## What you need

**Use Ubuntu.** It is free, the fastest path, and the same OS as the mail VM.

| Piece | Best choice |
|---|---|
| Your PC | **Ubuntu 22.04 or 24.04 LTS** (desktop, laptop, or Windows **WSL2 Ubuntu**) |
| Azure VM | **Ubuntu 22.04 LTS** (already set in `infra/main.bicep`) |
| Azure region | **Central India** if you are in India, else **East US** |

Windows works, but extra installs (Git Bash, PATH, line endings) slow you down. Ubuntu: `apt` installs Azure CLI, Git, Python, SSH in one go and `deploy.sh` runs as-is.

On Ubuntu PC:

```bash
sudo apt update
sudo apt install -y azure-cli git python3 openssh-client
az login
```

If the PC is Windows only: install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install), pick **Ubuntu**, then use those same commands inside Ubuntu.

Also:

1. `az login` on the subscription that holds the $1000 credit
2. Permission to create a resource group, a VM, ACS, and an Entra app (for SMTP)
3. One hostname you control, e.g. `mail.yourbrand.com`
4. About 20 minutes after DNS

## Deploy

From **Ubuntu** (or Ubuntu WSL) with Azure CLI:

```bash
cd azure-mail
chmod +x deploy.sh vm/install-mailcow.sh verify.sh
LOCATION=centralindia MAIL_HOSTNAME=mail.yourbrand.com ./deploy.sh
```

Use `LOCATION=eastus` if Central India is not available. Optional env: `RESOURCE_GROUP`, `DATA_LOCATION` (`United States`).

`deploy.sh` will:

1. Create `rg-azure-mail`
2. Create the Ubuntu 22.04 VM, NSG (22, 25, 80, 443, 587, 993), static IP
3. Create Email Communication Service + ACS + Azure-managed send domain
4. Create an Entra app + ACS SMTP username
5. SSH in and install **Mailcow** with ACS as `relayhost`

Credentials land in `azure-mail/.env` (gitignored). SSH key in `azure-mail/keys/`.

## DNS

**Receive** (every mailbox domain):

| Type | Name | Value |
|---|---|---|
| A | `mail` | VM public IP |
| MX | `@` | `mail.yourbrand.com` (priority 10) |

Turn **off** Cloudflare proxy (grey cloud) on `mail`.

**Send** — each From-domain must be verified on Azure Communication Services (Azure blocks VM port 25). Do that from Cloud Shell with `add-send-domain.sh` instead of the portal (see below). The From address in Mailcow must be a MailFrom on that verified, **linked** domain (or `DoNotReply@xxxx.azurecomm.net` for a first test).

After the A record exists:

```bash
az network public-ip update -g rg-azure-mail -n <pip-name> --reverse-fqdn mail.yourbrand.com.
```

(`deploy.sh` prints the pip name and tries this once.)

## Check send and receive

```bash
./verify.sh
python3 test_acs_send.py --to you@gmail.com
```

| Test | Pass means |
|---|---|
| `PORT25_BLOCKED` | Azure is doing the usual credit-subscription block. Expected. |
| `ACS_587_OPEN` | Send path exists. |
| `test_acs_send.py` arrives in Gmail (check spam) | ACS send works. |
| Gmail → `hello@yourdomain.com` shows in Mailcow | Receive works. |
| Mailcow webmail → Gmail | Full mailbox send via ACS relay. |
| https://www.mail-tester.com ≥ 9/10 | SPF/DKIM/DMARC are correct. |

Mailcow UI: `https://<VM-IP>`  
Default admin: `admin` / `moohoo` — **change immediately**.

Then: **Mail setup → Domains → add domain → Mailboxes → hello@…**  
Optional catch-all. For each domain, set the Mailcow “sender-dependent transport” is not required; `extra.cf` already relays **all** outgoing mail through ACS.

## Extra domains (Mailcow UI + one script, no portal)

Mailcow **is** the mail panel (like a private host): domains, mailboxes, aliases, webmail. Azure is only the outbound relay.

For a new brand `example.com`:

1. **Mailcow** (https://mail.yourbrand.com/admin): Domains → add `example.com` → **Add domain and restart SOGo**. Mailboxes → `hi@example.com`.
2. **DNS receive:** MX `@` → `mail.yourbrand.com` priority 10.
3. **DNS send + ACS** from Cloud Shell (prints the records, waits, links the domain, adds MailFrom `hi`):

```bash
cd azure-mail
chmod +x add-send-domain.sh
./add-send-domain.sh example.com hi
```

Override live resource names if needed: `RESOURCE_GROUP` `ACS_NAME` `EMAIL_NAME` `MAIL_HOSTNAME`. Defaults match `mailboxRg` / `mailboxCs` / `mail-box` / `mail.seethinajayadileep.dev`.

You still paste DNS at the registrar once (every host does: Google Workspace, Microsoft 365, Mailcow). You do **not** click Azure Email → SMTP → Connect after the first setup.

Azure-managed domain (`*.azurecomm.net`) is enough to prove send before you touch your real domains.

## What this does not do

- It does not unblock Azure outbound port 25
- It is not Microsoft 365 / Outlook mailboxes
- High-volume unsolicited mail will get ACS throttled

## Files

| Path | Role |
|---|---|
| `deploy.sh` | One-shot Azure + Mailcow install |
| `infra/main.bicep` | VM, NSG, IP, ACS, Email service |
| `vm/install-mailcow.sh` | Docker Mailcow + Postfix ACS relay |
| `verify.sh` | Port 25 vs 587 checks |
| `test_acs_send.py` | Authenticated send test |
| `add-send-domain.sh` | Extra domain: ACS verify + link + MailFrom (no portal) |

If `az ad app create` is denied, create an app registration in Entra, add a client secret, assign **Contributor** on the ACS resource, create an **SMTP username** on ACS, then put username/secret in the VM file `/opt/mailcow-dockerized/data/conf/postfix/sasl_passwd` and restart:

```bash
docker compose -f /opt/mailcow-dockerized/docker-compose.yml restart postfix-mailcow
```
