# Scout — AI Job Discovery

Full-stack app that scrapes job listings (Apify), cleans & deduplicates them, ranks with AI, and presents the best opportunities first.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, React, Tailwind CSS |
| Backend | Node.js, Express, TypeScript |
| Scraping | Apify Actor API (demo mode without token) |
| AI | OpenAI (heuristic ranking without key) |
| Cache | Redis (in-memory fallback) |
| Database | PostgreSQL (JSON file fallback) |

## Quick start

```bash
cp .env.example .env
npm install
npm run dev
```

- Frontend: http://localhost:3000  
- API: http://localhost:4000  
- Health: http://localhost:4000/api/health  

Without `APIFY_API_TOKEN` / `OPENAI_API_KEY` / Redis / Postgres the app runs fully in **demo mode** with curated sample jobs and heuristic AI ranking.

## Deploy: Vercel (frontend) + Railway (backend)

### 1. Backend on Railway

1. Create a new project at [railway.app](https://railway.app) → **Deploy from GitHub** → select this repo.
2. Set **Root Directory** to `backend`.
3. Railway will use `backend/railway.toml` (`npm run build` → `npm run start`).
4. Add plugins (recommended):
   - **PostgreSQL** → sets `DATABASE_URL`
   - **Redis** → sets `REDIS_URL` (or `REDIS_PRIVATE_URL`; map it to `REDIS_URL` if needed)
5. Set variables:

| Variable | Value |
|----------|--------|
| `CORS_ORIGIN` | Your Vercel URL, e.g. `https://scout.vercel.app` (comma-separate previews if needed) |
| `APIFY_API_TOKEN` | optional — live scrape |
| `OPENAI_API_KEY` | optional — LLM ranking |
| `OPENAI_MODEL` | `gpt-4o-mini` (optional) |
| `NODE_ENV` | `production` |

6. Generate a public domain for the service (e.g. `https://scout-api.up.railway.app`).
7. Confirm health: `GET https://<railway-domain>/api/health`

### 2. Frontend on Vercel

1. Import the same GitHub repo in [vercel.com](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Next.js** (auto).
4. Environment variable:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Your Railway public URL, e.g. `https://scout-api.up.railway.app` (no trailing slash) |

5. Deploy. Then update Railway `CORS_ORIGIN` to the Vercel URL if you deployed API first.

### 3. Wire them together

```
Browser → Vercel (Next.js)
            │
            └── NEXT_PUBLIC_API_URL → Railway (Express API)
                                         ├── Postgres
                                         └── Redis
```

Without Apify/OpenAI keys the API still works in **demo mode**.

## Docker

```bash
docker compose up --build
```

## API flow

```
User Search → Backend → Apify Actor → Wait → Dataset
  → Clean/Dedupe → AI Ranking → Ranked Jobs (+ cache & DB)
```

### Key endpoints

- `POST /api/search` — structured search + filters
- `POST /api/search/natural` — natural language search
- `GET /api/search/:id` — paginated results (infinite scroll)
- `POST /api/bookmarks` — save jobs
- `POST /api/resume` — resume upload for personalized ranking
- `POST /api/alerts` — email alert registration (stub delivery)
- `GET /api/export/:id.csv` / `.pdf` — export results
- `GET /api/recommendations` — from search history

## Architecture

```
backend/src/
  routes/          HTTP API
  services/apify/  Actor integration + demo data
  services/ai/     LLM + heuristic ranking
  services/jobs/   Normalize, dedupe, search orchestration
  services/cache/  Redis / memory
  services/database/ Postgres / file store
frontend/src/
  app/             Pages (Discover, Saved, Insights)
  components/      Search, JobCard, progress, insights
```

## AI ranking signals

Title relevance · skills match · location · company reputation · salary · recency · remote preference · employment type  

Each job returns `{ score, reason }` plus a 3-line summary, required/missing skills, resume tips, and interview difficulty.

## Scripts

```bash
npm run dev          # API + UI
npm run test         # backend unit tests
npm run build        # production build
npm run lint         # typecheck / next lint
```
