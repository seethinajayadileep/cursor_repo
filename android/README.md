# Cursor Pocket for Android (sideload)

This is a tiny WebView wrapper. It is **not** on the Play Store. You install it from your MacBook with Android Studio (USB).

Most people should skip this and use Chrome → **Add to Home screen** instead. See [MACBOOK_ANDROID.md](../MACBOOK_ANDROID.md).

## Build and install from the MacBook

1. Install [Android Studio](https://developer.android.com/studio) on the Mac.
2. On the phone: **Settings → About phone** → tap Build number 7 times → enable **USB debugging**.
3. Plug the phone into the Mac. Allow debugging.
4. Android Studio → **Open** → this `android/` folder.
5. Wait for Gradle sync.
6. Green **Run** button, pick your phone.

The first screen asks for the laptop URL from the Mac terminal (`http://192.168.…:8787` or the `https://….trycloudflare.com` link). Then you get the same Pocket UI (PIN, prompt, live log).

Menu (**⋮**) → **Change laptop URL** if you restart Pocket with a new tunnel URL.
