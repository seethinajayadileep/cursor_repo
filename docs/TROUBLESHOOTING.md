# Troubleshooting

| Symptom | Fix |
|---|---|
| API won't start | Check `PORT`, rebuild packages, ensure sqlite path writable |
| Login fails | Run `db:seed` or sign up a new user |
| Microphone denied | Allow OS/browser permission or use DEMO MODE / manual input |
| Blank AI answers | Confirm `/api/health` and provider; DEMO MODE should always respond |
| PDF parse empty | Ensure text-based PDF; scanned PDFs need OCR (future enhancement) |
| Electron blank window | Start web+api first; check `INTERVIEWPILOT_WEB_URL` |
