# Cursor Pocket for Android (sideload APK)

This is a real Android app (`app.cursorpocket`). It is **not** on the Play Store. It opens the Pocket phone UI in a WebView and shows a native notification when a run finishes.

## Install on the phone (easiest)

1. On the Mac: `python3 -m cursor_pocket --workspace ~/your-project`
2. On the phone, open the Pocket URL from the Mac terminal.
3. Tap **Install Android app (APK)** (only shown when this repo has a built APK).
4. Allow install from Chrome / Files.
5. Open **Cursor Pocket**, paste the same laptop URL, enter the PIN.

You can also download `cursor-pocket.apk` from the GitHub Action named **android-apk**, or from the laptop at `/apk/cursor-pocket.apk`.

## Build on the Mac / Linux

Need JDK 17+ and the Android SDK.

```bash
cd android
echo "sdk.dir=$ANDROID_HOME" > local.properties   # or ANDROID_SDK_ROOT
chmod +x gradlew
./gradlew assembleDebug
mkdir -p dist
cp app/build/outputs/apk/debug/app-debug.apk dist/cursor-pocket.apk
```

Then restart Pocket so the phone page offers the download.

## Android Studio

1. Enable **USB debugging** on the phone.
2. Android Studio → **Open** → this `android/` folder.
3. Green **Run**.

The first screen asks for the laptop URL (`http://192.168.…:8787` or the `https://….trycloudflare.com` link). Menu (**⋮**) → **Change laptop URL** if the tunnel URL changes.
