# GoLiveCheck

**Working name:** GoLiveCheck  
**Repo / package (planned):** `golivecheck-agent`  
**CLI (planned):** `golivecheck` or `glc`

A testing agent another AI or a developer can call **before shipping**.

Point it at a site you own. In one run it checks:

1. User flow (English steps, optional AI)
2. API smoke
3. Accessibility (WCAG)
4. Safe security (headers, cookies, CORS — **no hacking**)

Then it writes **one report**: pass / fail and what to fix.

---

## Read these if you are an AI

| File | Read when |
|---|---|
| [IDEA.md](./IDEA.md) | First. What we are building, who it is for, walls. |
| [ROADMAP.md](./ROADMAP.md) | Full build path: spec → v0 → real app → npm. |
| [AGENTS.md](./AGENTS.md) | You will **implement or change** this repo. |
| [SKILL.md](./SKILL.md) | You will **run** GoLiveCheck for a user (CLI or MCP). |
| [PRODUCT.md](./PRODUCT.md) | Features, uniqueness, what we will not build. |
| [PLAN.md](./PLAN.md) | Day-1 coding order (Phase 1 only). |

Do not invent extra product scope. If IDEA.md and the user disagree, **ask** — do not expand into pentest, mobile, or SaaS.

---

## Humans (short)

```bash
# v0 (not implemented in this folder yet — spec only)
npx golivecheck-agent run
npx golivecheck-agent run --only security,a11y
npx golivecheck-agent report
```

This folder is the **source of truth for the idea**. Code comes after an implementer follows `PLAN.md` without breaking `IDEA.md` walls.
