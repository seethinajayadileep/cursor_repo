# Development

## Scripts
- `npm run dev` — API + web
- `npm test` — Vitest unit tests
- `npm run build` — build all workspaces
- `npm run dev:desktop` — Electron against local web URL

## Demo mode
When no AI keys are present (or `DEMO_MODE=true`), the API uses `DemoAIProvider` and the UI can simulate transcripts.

## Adding a language
1. Add code/name to `SUPPORTED_LANGUAGES` in `packages/shared`
2. Add UI catalog in `apps/web/src/i18n`
3. Map STT locale in speech providers / session page
