# Architecture

InterviewPilot AI is a TypeScript monorepo with three apps and shared packages.

## Apps
- **web** — React SPA (landing, auth, dashboard, session wizard, live session, mock interviews, documents, settings, billing, help)
- **api** — Express REST API with JWT auth, SQLite (local) / Postgres-ready URL config, document pipeline, AI routes
- **desktop** — Electron shell with `contextIsolation`, no `nodeIntegration`, preload IPC bridge, tray, global shortcuts

## Packages
- `shared` — domain types and utilities
- `config` — environment loading
- `database` — SQLite schema + client
- `documents` — extract/clean/chunk/embed/resume parse/RAG retrieve
- `ai` — prompts, question detection, context compression, provider abstraction (demo/OpenAI/Anthropic/Google/local)
- `speech` — audio source + STT provider abstractions
- `ui` — shared UI helpers

## Data flow
Audio → STT (partial/final) → question detection (debounced) → RAG retrieve → AI stream → UI

## Security boundary
Renderer never receives Node APIs or secrets. API keys stay on the server / main process env.
