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

**Which Cursor screen?** Both the file editor and the Agents chat are the same app (`Cursor.app`).

- Phone **Agent**: local IDE box (**Cmd+I**).
- Phone **Cloud**: opens **New Chat / Agents**, clicks the bottom prompt, pastes, and Send. That is the Cloud Agents thread (left sidebar, Cloud picker).

Keep Cursor in front, Mac awake and unlocked. The Mac still needs internet for Cloud Agents.

Example folder: `/Users/you/Projects/my-app`

### 2. Accessibility permission (required)

macOS has **two** different Accessibility screens. Pocket needs the **permission** list, not Zoom / VoiceOver.

**Do not** open the sidebar item **System Settings → Accessibility** (that is display and hearing features). There is no Terminal toggle there.

**Do this instead:**

1. Apple menu → **System Settings** (older Macs: **System Preferences**).
2. In the search box at the top, type **Accessibility**.
3. Choose **Privacy & Security → Accessibility** (or **Security & Privacy → Privacy → Accessibility** on older macOS).  
   You should see a list of apps that can **control this Mac**, with on/off switches — not VoiceOver / Zoom.
4. Click the **+** button. Add **Terminal** (`Applications → Utilities → Terminal`). If you use iTerm, add **iTerm**. If a dialog later asks for **Python**, turn that on too.
5. Turn the switch **on**. You may need to enter your Mac password.

Fastest way — paste this in Terminal; it jumps to the right pane:

```bash
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
```

If that opens Privacy & Security but not the list, scroll the right-hand page until you see **Accessibility** under permissions (same group as Camera, Microphone, Automation).

Without this permission, the phone can still pair, but Cursor **Send will not be clicked**.

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
cd /Users/jaya/Desktop/Cursor-Pocket
python3 -m cursor_pocket --workspace /Users/you/Projects/my-app
```

`--demo` is ignored when Cursor is installed (Pocket 0.3.3+), so Send still works. The phone badge should say **live**. If it still says **demo**, you are on an old copy — `git pull` — or you passed `--fake`.

Use the **real path** of the project you have open in Cursor.

**Phone on mobile data / another Wi-Fi** (both devices online). First install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/) **or** [ngrok](https://ngrok.com/download), then:

```bash
cd /Users/jaya/Desktop/Cursor-Pocket
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
3. Phone: open Pocket, type the prompt, pick **Agent** (local Cursor) or **Cloud** (Agents chat), tap **Send to laptop**.
4. Cursor on the Mac gets the text and Send is clicked. The phone shows the reply and what files changed.
5. You get a notification when it is **Finished** or **Failed**: phone banner (Enable notifications, or the Android APK for lock-screen alerts) and a Mac notification from Pocket.
6. Back at the Mac, review the diff in Cursor.

**Agent** pastes into the local composer (Cmd+I). **Cloud** opens the Agents chat, clicks the prompt box, and sends. Use `--cli` if you want Ask/Plan through Cursor CLI instead.

---

## Stop

On the Mac terminal: **Ctrl+C**. The phone cannot send prompts until you start Pocket again.

---

## First test (no real Cursor edits)

`--fake` only checks that the phone can pair. **Cursor stays idle.** The phone will show **Finished** with fake text. That is expected.

```bash
cd /Users/jaya/Desktop/Cursor-Pocket
python3 -m cursor_pocket --fake --pin 123456
```

On the phone use PIN `123456`, send any text, wait for **Finished**. Then **Ctrl+C** and start the real command from Part 2 if you want Cursor to actually run.

If you already started with `--demo` on a Mac that has Cursor (0.3.3+), Pocket sends for real and the phone should say **live**, not demo.

---

## If the phone cannot open the URL

- Same Wi-Fi: both on the same network. “Guest” Wi-Fi often blocks phone→Mac. Use the Mac hotspot or `--online`.
- `--online`: Mac must have `cloudflared` or `ngrok`. Phone needs internet. Anyone with the URL still needs the PIN.
- Mac firewall blocked Python: System Settings → Network → Firewall → Options → allow Python.
- Wrong project path: `--workspace` must be the folder Cursor has open.
- `No Cursor desktop`: install Cursor, or pass `--demo` / `--cli`.
- Send is not clicked: enable **Privacy & Security → Accessibility** for Terminal/Python (not the VoiceOver/Zoom Accessibility page). Paste `open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"` in Terminal.
- Phone or Mac says **demo** / `Mode: DEMO`: `git pull` (need 0.3.3+), Ctrl+C, start again. `--demo` is ignored when Cursor is installed. `--fake` still shows demo and will not click Cursor. Re-open the phone URL.
- Send goes to the wrong chat: on the phone pick **Cloud** for the Agents / Cloud prompt box, or **Agent** for the local Cmd+I composer. Leave Cursor in front.
