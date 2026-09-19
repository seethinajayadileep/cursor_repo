# AI Pipeline

## Prompt module
Centralized templates in `packages/ai/src/prompts.ts` (resume, technical, behavioral, coding, system design, meeting summary, mock interviewer, document QA).

## Question detection
Heuristic patterns first (`question-detector.ts`). Debounce before expensive LLM calls. API endpoint: `POST /api/ai/detect-question`.

## Answer generation
`POST /api/ai/answer` builds context from resume JSON, JD, retrieved chunks, recent transcript, instructions, then calls the configured provider.

## Rules
- Prefer user documents over generic assumptions
- Never invent employers, metrics, certifications
- Stream tokens to the UI when possible
- Cancel/ignore stale generations at the client when a newer question arrives (`answeringRef` guard)
