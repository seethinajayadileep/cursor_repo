# Changes Made

- Switched from a manual `thebibliography` to BibTeX (`IEEEtran.bst` + `references.bib`). This is the usual cause of `[?]` in locally compiled PDFs when only `pdflatex` is run, or when a BibTeX workflow is used against a hand-written bibliography.
- Retitled the paper to *WebSentinel: An Explainable Website Security Assessment Framework for Phishing Risk Analysis* so it does not claim a completed ML phishing detector.
- Replaced raw `INSERT ...` / `[RESULT REQUIRED]` text in the PDF with camera-ready affiliation wording, an evaluation protocol, and qualitative source-inspection observations.
- Removed the Acknowledgment section from the PDF (affiliation/supervisor text remains as a source comment).
- Default author list remains the full six-person project team; Option B (research-paper trio) is still commented in `main.tex`. Affiliation placeholders are editable macros, not ugly inline tokens.
- Rewrote the abstract, contributions, conclusion, and evaluation sections while keeping the implemented-versus-planned distinction.
- Added a verified SSRF control table (implemented vs required/planned).
- Rebuilt TikZ figures with solid (implemented) vs dashed (planned) borders and a legend.
- Removed empty metric tables from the compiled paper. Templates remain in `tables/evaluation_tables.tex`.
- Compiled with `pdflatex` → `bibtex` → `pdflatex` → `pdflatex` and verified the PDF.
- Reduced the bibliography from 33 entries to 17 core sources (user request: 15--18).

# Implemented Features Described

Verified against `seethinajayadileep/WebSentinel` commit `7d8822f`:

- Chrome Manifest V3 popup (`activeTab`, origin-only POST)
- Express `GET /health` and `POST /check` (8 kB body limit)
- HTTPS scheme check
- TLS check via `ssl-checker` (8 s timeout)
- WHOIS HTML scrape for domain age, update recency, DNSSEC string
- Additive rule score and Safe / Suspicious / High risk bands
- Human-readable reason strings
- Unsupported-scheme rejection
- Vercel deployment configuration
- One Node assertion that `chrome://` is rejected

# Planned Features Described

- FastAPI, React/TypeScript dashboard, PostgreSQL, Redis/Celery
- RDAP (file exists, empty), DNS, redirects, technology, IP/hosting
- Threat-intelligence / breach APIs
- Machine-learning classifier and SHAP
- Authentication, scan history, reports, monitoring
- Production SSRF resolver guard, rate limiting, redirect revalidation
- Docker / Nginx / CI and the full pytest / Vitest / Playwright / ZAP suite

# Experimental Evidence Available

None. No notebooks, metric CSVs, scan logs, or trained model artifacts were found. Results in the paper are limited to observations from source inspection (score formula, reason list, origin-only privacy, WHOIS fragility, 85 vs 100 scale).

# Experimental Evidence Still Required

- Licensed dataset name, counts, dates, and split
- Rule-engine precision/recall on a labelled hold-out
- ML metrics after a model is trained
- Mean/median/min/max scan latency and timeout rate
- Executed functional and SSRF test results
- OWASP ZAP report against the team deployment

# Remaining Manual Information

- University name
- Department
- City
- Country
- Per-author emails (corresponding email currently uses the public Dileep address)
- Supervisor / funding acknowledgment if the venue requires one
- Whether to switch from Option A (six authors) to Option B (three)

Edit the macros `\WSDept`, `\WSUniv`, `\WSCity`, `\WSCountry`, and `\WSEmail` at the top of `main.tex` before camera-ready submission.

# Compilation Status

- `main.pdf` compiled successfully (TeX Live 2023, IEEEtran 1.8b / IEEEtran.bst 1.14)
- Pages: 10
- Unresolved citations: 0
- Unresolved cross-references: 0
- Visible PDF tokens checked: no `[?]`, `??`, `INSERT`, `RESULT REQUIRED`, `TODO`, `TBD`, or `XXX`
- Major overfull boxes: none after the author-block wrap
- Bibliography entries in the PDF: 17 (trimmed from 33 at the authors' request; all remaining entries are cited)
