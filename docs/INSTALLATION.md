# Installation

1. Install Node.js 20+
2. `cp .env.example .env`
3. `npm install`
4. Build shared packages: `npm run build -w @interviewpilot/shared && npm run build -w @interviewpilot/config && npm run build -w @interviewpilot/database && npm run build -w @interviewpilot/documents && npm run build -w @interviewpilot/ai && npm run build -w @interviewpilot/speech`
5. `npm run db:migrate -w @interviewpilot/api`
6. `npm run db:seed -w @interviewpilot/api`
7. `npm run dev`

Open http://localhost:5173
