# Deployment

## Web frontend
Build `apps/web` (`npm run build -w @interviewpilot/web`) and deploy `apps/web/dist` to Vercel, Cloudflare Pages, Netlify, or any static host. Point API calls via reverse proxy or set absolute API origin.

## API
Run `apps/api` as a Node service (container/VPS). Set `DATABASE_URL`, `AUTH_SECRET`, provider keys, `CORS_ORIGIN`.

## Desktop Windows artifacts
```bash
npm run pack -w @interviewpilot/desktop
```
Outputs in `apps/desktop/release/`.
On non-Windows agents, use electron-builder with Wine or a Windows CI runner to produce `.exe`.
