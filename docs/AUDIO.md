# Audio

## Abstraction
`AudioSource` interface with `MicrophoneAudioSource`, `BrowserAudioSource`, `DesktopAudioSource`.

## STT
`SpeechToTextProvider`: `DemoSpeechProvider`, `BrowserSpeechProvider`, `LocalSpeechProvider`, `CloudSpeechProvider`.

## Browser limitations
Tab/system audio is inconsistent. The web app shows an explicit notice and offers DEMO MODE + manual question input.

## Desktop
Electron can surface OS permission prompts and optional system-audio paths where supported. Always user-controlled — no silent capture.
