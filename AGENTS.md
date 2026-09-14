# AGENTS.md (this workspace)

This GitHub repo currently holds **two different things**. Do not mix them.

## 1. Existing app — PII redaction

Python tool: read a PDF / ticket log, find PII, write a redacted `.docx`.

See the root `README.md`. Do not turn this into a testing agent.

## 2. New product spec — GoLiveCheck

We are **planning** an open-source testing agent. The source of truth is:

**[golivecheck/README.md](./golivecheck/README.md)**

Read in this order:

1. [golivecheck/IDEA.md](./golivecheck/IDEA.md) — what we are building
2. [golivecheck/AGENTS.md](./golivecheck/AGENTS.md) — how to implement
3. [golivecheck/SKILL.md](./golivecheck/SKILL.md) — how a user/AI runs it
4. [golivecheck/PRODUCT.md](./golivecheck/PRODUCT.md) — feature list
5. [golivecheck/PLAN.md](./golivecheck/PLAN.md) — build order

If the user asks you to **build the testing agent**, follow those files. Create a new package; do not implement it inside `redact/`.
