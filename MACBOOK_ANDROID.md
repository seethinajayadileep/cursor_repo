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

Open your project in **Cursor desktop**. Leave that window open. Pocket clicks **Send** in this app; it does not use a separate hidden agent unless you pass `--cli`.

Example folder: `/Users/you/Projects/my-app`

### 2. Accessibility (required)

On the Mac: **System Settings → Privacy & Security → Accessibility**. Turn on **Terminal** (or **iTerm** / **Python**, whichever runs Pocket). Without this, the phone cannot click Send.

### 3. Python

```bash
python3 --version
```

Need 3.10 or newer.

### 4. Get Cursor Pocket on the Mac

Folder must contain `cursor_pocket/` and `web/`.

---

## Part 2 — Start Pocket on the Mac (every time you want the phone)

Leave **Cursor desktop** open on your project. The Mac must stay **awake and unlocked**. Open a terminal **and do not close it**.

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

Google Play has no Cursor app. Pocket **is** the Android app. Use the APK (home-screen icon + native notification) or Chrome “Add to Home screen”.

### Option A — APK (the actual app)

1. Start Pocket on the Mac (Part 2).
2. On the phone, open Chrome to the URL printed in the Mac terminal.
3. Tap **Install Android app (APK)** and open the downloaded file. Allow install from this source if Android asks.
4. Open the **Cursor Pocket** icon. Paste the laptop URL, then the PIN.

If the button is missing, build once: `cd android && ./gradlew assembleDebug` (see [`android/README.md`](android/README.md)).

### Option B — Chrome home screen shortcut

1. On the phone, open **Chrome**.
2. Type the URL from the Mac terminal (or scan the QR).
   - Same Wi-Fi: `http://192.168.…:8787`
   - `--online`: `https://….trycloudflare.com`
3. Enter the **PIN** from the Mac. Tap **Pair with laptop**.
4. Chrome menu (**⋮**) → **Add to Home screen** or **Install app**.
5. Open the new **Pocket** icon on the home screen like any other app.

With `--online` the URL is HTTPS, so Chrome can install it as a real standalone app and can show a notification when a run finishes.

**Every day after that:** start Pocket on the Mac first, then tap the Pocket icon on the phone. If the PIN changed (you restarted Pocket without `--pin`), pair again.

---

## Part 4 — Daily use

1. Mac: open the project in **Cursor desktop**. Keep the Mac awake and unlocked.
2. Mac: start Pocket. Leave it running.
3. Phone: open Pocket, type the prompt, tap **Send to laptop**.
4. Cursor on the Mac gets the text and Send is clicked. The phone shows **Cursor’s reply** and **what files it fixed**.
5. You get a notification when it is **Finished** or **Failed**.
6. Back at the Mac, review the diff in Cursor.

Desktop mode pastes into the Agent composer (Cmd+I). Use `--cli` if you want Ask/Plan through Cursor CLI instead.

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
- `No Cursor desktop`: install Cursor, or pass `--demo` / `--cli`.
- Send is not clicked: enable Accessibility for Terminal/Python.
- Mac locked or asleep: unlock it; automation cannot click Send on the lock screen.
