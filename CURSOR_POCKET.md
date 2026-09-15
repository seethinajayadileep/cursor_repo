# Cursor Pocket

**Send Cursor prompts from an Android phone. They run on your laptop. You get the live log and a ping when it finishes. The phone never talks to Cursor Cloud.**

Cursor has no Android app. The iOS app only drives **cloud** agents. If you (or a friend) sit on a laptop all day because that is the only place a local Cursor agent will run, Pocket is the missing remote: a tiny daemon on the laptop plus a phone web app on the same Wi-Fi.

```text
  Android Chrome                    Laptop (stays on)
  ┌─────────────────┐               ┌──────────────────────────┐
  │ Type a prompt   │  same Wi-Fi   │ python3 -m cursor_pocket │
  │ Agent / Ask /   │ ────────────► │ PIN pair  →  `agent -p`  │
  │ Plan            │  live SSE     │ Cursor CLI edits the repo│
  │ Notification    │ ◄──────────── │ stream-json events       │
  └─────────────────┘               └──────────────────────────┘
```

No Play Store build is required. Chrome on Android opens the laptop URL and can “Add to Home screen”.

---

## Why this exists

| Official option | Why it does not solve this |
| --- | --- |
| Cursor iOS app | Cloud agents only, not the local laptop session |
| Cursor Android app | Does not exist |
| Cloud Agents in the browser | Needs Cursor cloud, not a fully local/offline control path |

**What “offline” means here:** the *remote control path* is offline. Phone and laptop talk only on LAN, USB `adb reverse`, or the laptop’s hotspot. There is no Pocket server in the cloud, no account, no telemetry.

Cursor CLI on the laptop still uses whatever that machine already uses for models (Cursor API, or a local model if you have one). Pocket does not add a second cloud.

---

## Features (v0.1)

- Pair the phone with a 6-digit PIN (printed in the terminal and on the laptop `/host` page with a QR code).
- Send a prompt; choose **Agent** (edit code), **Ask** (read-only), or **Plan**.
- Point at one or more project folders (`--workspace`, repeatable).
- Live tool/assistant log over Server-Sent Events.
- Banner, vibration, chime, and (on HTTPS or `localhost`) a system notification when a run ends.
- Cancel a run; send a follow-up that resumes the Cursor CLI session.
- One agent process at a time so two prompts cannot stomp the same repo.
- `--demo` mode to try the phone UI without Cursor CLI.
- Optional `--https` (self-signed) so Android can install the PWA and show notifications on Wi-Fi.
- Zero Python dependencies. Stdlib only.

### Later (good first issues)

- mDNS / “Cursor Pocket” showing up without typing an IP
- Native Android wrapper (Kotlin or Capacitor) with a foreground service so the phone can sleep
- Approvals on the phone when you omit `--force`
- Pairing over a QR that includes a one-time token
- Tailscale / WireGuard notes for when you *do* want the phone off-LAN (optional; not the default)

---

## Use it

### 1. Laptop

Install [Cursor CLI](https://cursor.com/docs/cli/overview) and log in once (`agent login`) the same way you already use Cursor.

From this repo (Python 3.10+):

```bash
cd path/to/this-repo
python3 -m cursor_pocket --workspace ~/src/the-project
```

Leave that terminal open. It prints a PIN and a phone URL, for example `http://192.168.1.20:8787`.

More than one repo:

```bash
python3 -m cursor_pocket --workspace ~/src/app --workspace ~/src/api
```

Try the UI without calling Cursor:

```bash
python3 -m cursor_pocket --demo --pin 123456
```

Laptop pairing page (QR + PIN, localhost only): [http://127.0.0.1:8787/host](http://127.0.0.1:8787/host)

### 2. Android phone

1. Same Wi-Fi as the laptop, **or** join the laptop’s hotspot, **or** USB (below).
2. Chrome → open the URL from the terminal.
3. Type the PIN.
4. Write a prompt → **Send to laptop**.
5. Keep the page open. When Cursor finishes you get a live “Finished” state, a chime, and a notification if the browser allows it.

Chrome menu → **Add to Home screen** / **Install app** gives an icon. Full install + notifications on Wi-Fi need a [secure context](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts): use USB localhost **or** start with `--https` and accept the self-signed warning once.

### 3. USB, no Wi-Fi

On the laptop (with [platform-tools](https://developer.android.com/tools/releases/platform-tools) / `adb`):

```bash
adb reverse tcp:8787 tcp:8787
```

On the phone open `http://127.0.0.1:8787`. That is localhost, so Chrome treats it as secure (notifications + install work).

### Flags

| Flag | Meaning |
| --- | --- |
| `--workspace PATH` | Project Cursor may edit (repeatable). Default: current directory |
| `--pin 123456` | Fix the PIN (otherwise random each start) |
| `--demo` | Fake a run; no `agent` binary needed |
| `--https` | Self-signed TLS (cert in `~/.cursor-pocket/`) |
| `--no-force` | Do not pass `--force` to CLI (commands may wait for approval on the laptop) |
| `--no-trust` | Do not pass `--trust` |
| `--host` / `--port` | Bind address (default `0.0.0.0:8787`) |
| `--name` | Label shown on the phone |

---

## Security (read this)

Anyone on the LAN who knows the PIN can send prompts. With default `--force --trust`, Cursor CLI can edit files and run commands **as you** on the laptop.

- Only start Pocket on networks you trust.
- Do not port-forward `8787` to the internet.
- Restart the laptop process to mint a new PIN and drop paired phones.
- Eight wrong PINs lock pairing until restart.
- The PIN is never served to the phone UI; `/api/host` only answers `127.0.0.1`.

This is a power-user remote, not a multi-tenant SaaS.

---

## How it is built

| Piece | What it is |
| --- | --- |
| `cursor_pocket/` | Python 3 daemon: PIN auth, job queue, SSE, static files |
| `cursor_pocket/runner.py` | Spawns `agent -p --output-format stream-json --workspace …` |
| `web/` | Mobile-first UI + laptop `/host` page (no npm build) |
| `tests/` | Stdlib `unittest` |

Phone → `POST /api/pair` → bearer token in `localStorage` → `POST /api/jobs` → laptop thread runs Cursor CLI → `GET /api/jobs/:id/events` streams compact events.

---

## Open source

Cursor Pocket files (`cursor_pocket/`, `web/`, `tests/test_*.py` for Pocket, `CURSOR_POCKET.md`) are **MIT**. See [cursor_pocket/LICENSE](cursor_pocket/LICENSE).

**Anyone can use it** by cloning this repo and running `python3 -m cursor_pocket`. There is no API key for Pocket itself.

**Anyone can fork it.** Keep the security warnings. Please do not add analytics. If you publish a Play Store wrapper, say clearly that prompts execute with the laptop user’s full agent permissions.

### Suggested public repo shape

If you split this into its own GitHub repo (`cursor-pocket`):

1. Copy `cursor_pocket/`, `web/`, `tests/test_auth.py`, `tests/test_jobs.py`, `tests/test_parse.py`, `tests/test_api.py`, `tests/test_net.py`, this file, `pyproject.toml`, and `.github/workflows/cursor-pocket.yml`.
2. Put this file at `README.md`.
3. Tag `v0.1.0`.
4. GitHub → Settings → Features: Issues + Discussions.
5. Topics: `cursor`, `android`, `offline`, `lan`, `pwa`.

### Contribute

```bash
python3 -m unittest discover -s tests -v
```

PRs that stay stdlib-only for the daemon are easiest to merge. The vendored QR library is [davidshimjs/qrcodejs](https://github.com/davidshimjs/qrcodejs) (MIT).

---

## Tests

```bash
python3 -m unittest discover -s tests -v
```

`--demo` is also the manual test: pair with `--pin 123456`, send “hello”, watch the log hit **Finished**, and confirm the phone banner/chime.
