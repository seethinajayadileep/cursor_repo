# InterviewPilot AI

**Your real-time AI copilot for interviews, meetings and technical conversations.**

InterviewPilot AI is an original desktop + web product for interview preparation, live conversation assistance, coding support, mock interviews, document-aware answers (RAG), and meeting notes.

> Practice and productivity tool — not a guarantee of interview success or 100% accuracy. Some interviews prohibit AI assistance. Obtain consent before recording.

## Features

- Real-time speech transcription (demo / browser / cloud abstractions)
- Real-time AI answer suggestions with streaming UI
- Resume-aware and job-description-aware answers (no invented experience)
- Document upload + RAG (PDF, DOCX, TXT)
- Question detection (rules + classification)
- Coding / HR / behavioral / system-design modes
- Mock interviews with practice feedback
- Meeting summaries, action items, session history
- Multilingual architecture (English, Hindi, Telugu initially)
- Electron desktop app (tray, shortcuts, always-on-top option)
- **DEMO MODE** — fully usable without paid API keys

## Architecture

Monorepo:

```
apps/
  web/       React + TypeScript + Vite + Tailwind
  api/       Express + SQLite API
  desktop/   Electron (secure preload bridge)
packages/
  shared/ ai/ speech/ documents/ database/ config/ ui/
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

- Node.js 20+
- npm 10+
- Optional: OpenAI / Anthropic / Google API keys for live AI
- Windows 10/11 for native installer artifacts (electron-builder)

## Installation

```bash
cp .env.example .env
npm install
npm run build -w @interviewpilot/shared
npm run db:migrate -w @interviewpilot/api
npm run db:seed -w @interviewpilot/api
```

## Development

```bash
npm run dev
```

- Web: http://localhost:5173
- API: http://localhost:8787/api/health

Demo user (after seed): `demo@interviewpilot.ai` / `demo12345`

Desktop (with web+api running):

```bash
npm run build -w @interviewpilot/desktop
npm run dev -w @interviewpilot/desktop
```

## Environment variables

See [.env.example](.env.example). Important:

| Variable | Purpose |
|---|---|
| `AI_PROVIDER` | `demo` / `openai` / `anthropic` / `google` / `local` |
| `OPENAI_API_KEY` | Optional cloud AI |
| `STT_PROVIDER` | `demo` / `browser` / `local` / `cloud` |
| `DATABASE_URL` | SQLite `file:...` or Postgres URL |
| `AUTH_SECRET` | JWT signing secret |
| `DEMO_MODE` | Force demo providers |

Never commit a filled `.env`.

## Testing

```bash
npm test
```

Automated tests use mocks/demo providers — no paid APIs required.

## Building Windows app

On a Windows host (or CI with Windows):

```bash
npm run build -w @interviewpilot/desktop
npm run pack -w @interviewpilot/desktop
```

Expected outputs under `apps/desktop/release/`:

- `InterviewPilot-AI-Setup.exe`
- `InterviewPilot-AI-Portable.exe`

On Linux CI this environment can compile Electron main/preload and prepare builder config; generating `.exe` may require Wine or a Windows runner. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Documentation

- [ARCHITECTURE](docs/ARCHITECTURE.md)
- [INSTALLATION](docs/INSTALLATION.md)
- [DEVELOPMENT](docs/DEVELOPMENT.md)
- [AI_PIPELINE](docs/AI_PIPELINE.md)
- [AUDIO](docs/AUDIO.md)
- [DOCUMENTS](docs/DOCUMENTS.md)
- [SECURITY](docs/SECURITY.md)
- [DEPLOYMENT](docs/DEPLOYMENT.md)
- [TROUBLESHOOTING](docs/TROUBLESHOOTING.md)

## Legal / ethical notice

Users are responsible for complying with interview and meeting rules. The product does not implement proctoring evasion, hidden capture, or secret recording. Screenshot/image context requires explicit user action.
