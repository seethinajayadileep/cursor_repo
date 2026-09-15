# MacBook + Android (step by step)

You write code in **Cursor on the MacBook**. The Android phone is only a remote: you type a prompt there, Cursor still runs on the Mac. There is **no Cursor app on the Play Store**. Pocket is the Android app. You install it from the Mac, not from Google Play.

```text
MacBook (Cursor + your project)          Android phone
  Cursor IDE stays open                    Pocket app (home screen icon)
  Pocket helper stays running     <------> type prompt, see when it finishes
```

---

## Part 1 — MacBook (one time)

### 1. Keep using Cursor like you do now

Open your project in Cursor. That folder is the one Pocket will send prompts into.

Example: Cursor has `/Users/you/Projects/my-app` open.

### 2. Install Cursor CLI once

Pocket talks to Cursor through the CLI (`agent`), not by clicking inside the IDE window.

In **Cursor → Terminal** (or Mac Terminal):

```bash
curl https://cursor.com/install -fsS | bash
```

Close and reopen the terminal, then:

```bash
agent login
```

Sign in with the same Cursor account you already use.

Check:

```bash
agent --version
```

### 3. Get Cursor Pocket on the Mac

If this repo is already on the Mac:

```bash
cd /path/to/cursor_repo
```

That folder must contain `cursor_pocket/` and `web/`.

### 4. Python

macOS already has `python3`. Check:

```bash
python3 --version
```

You need 3.10 or newer. If it is older: [python.org/downloads](https://www.python.org/downloads/) or `brew install python`.

---

## Part 2 — Start Pocket on the Mac (every time you want the phone)

Leave Cursor open on your project. Open a terminal **and do not close it**.

**Same Wi-Fi as the phone** (home router, or turn on Mac hotspot and join it from Android):

```bash
cd /path/to/cursor_repo
python3 -m cursor_pocket --workspace /Users/you/Projects/my-app
```

Use the **real path** of the project you have open in Cursor.

**Phone on mobile data / another Wi-Fi** (both devices online). First install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/) **or** [ngrok](https://ngrok.com/download), then:

```bash
cd /path/to/cursor_repo
python3 -m cursor_pocket --online --workspace /Users/you/Projects/my-app
```

You should see a **PIN** (six digits) and a **phone URL**.

Optional: on the Mac, open [http://127.0.0.1:8787/host](http://127.0.0.1:8787/host) to see the QR code.

If macOS asks to allow Python to accept incoming connections, click **Allow**.

Sleeping the Mac stops Pocket. Plug in power, and in **System Settings → Battery → Options** turn off “Put hard disks to sleep” if you want it to keep running.

---

## Part 3 — Install the app on Android

Google Play has no Cursor app. Install Pocket like this (this **is** the Android app):

1. On the phone, open **Chrome**.
2. Type the URL from the Mac terminal (or scan the QR).
   - Same Wi-Fi: `http://192.168.…:8787`
   - `--online`: `https://….trycloudflare.com`
3. Enter the **PIN** from the Mac. Tap **Pair with laptop**.
4. Chrome menu (**⋮**) → **Add to Home screen** or **Install app**.
5. Open the new **Pocket** icon on the home screen like any other app.

With `--online` the URL is HTTPS, so Chrome can install it as a real standalone app and can show a notification when a run finishes.

**Every day after that:** start Pocket on the Mac first, then tap the Pocket icon on the phone. If the PIN changed (you restarted Pocket without `--pin`), pair again.

Sideload a native APK from Android Studio instead: see [`android/README.md`](android/README.md).

---

## Part 4 — Daily use

1. Mac: open the project in Cursor.
2. Mac: start Pocket in a terminal (`--workspace` = that project). Leave it running.
3. Phone: open Pocket, type what you want Cursor to do, tap **Send to laptop**.
4. **Keep the phone app open** until you see **Finished**.
5. On the Mac, the files in Cursor will have changed. Review the diff there like you always do.

Modes on the phone:

- **Agent** — edit the project (normal)
- **Ask** — read only
- **Plan** — plan first

---

## Stop

On the Mac terminal: **Ctrl+C**. The phone cannot send prompts until you start Pocket again.

---

## First test (no real Cursor edits)

```bash
cd /path/to/cursor_repo
python3 -m cursor_pocket --demo --pin 123456
```

On the phone use PIN `123456`, send any text, wait for **Finished**. Nothing in your project is changed.

---

## If the phone cannot open the URL

- Same Wi-Fi: both on the same network. “Guest” Wi-Fi often blocks phone→Mac. Use the Mac hotspot or `--online`.
- `--online`: Mac must have `cloudflared` or `ngrok`. Phone needs internet. Anyone with the URL still needs the PIN.
- Mac firewall blocked Python: System Settings → Network → Firewall → Options → allow Python.
- Wrong project path: `--workspace` must be the folder Cursor has open.
- `No Cursor CLI (agent) found`: do Part 1 step 2 again, then open a **new** terminal.
