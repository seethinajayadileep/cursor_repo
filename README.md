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
