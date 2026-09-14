# WebSentinel IEEE Research Paper

This directory contains an IEEE conference paper for the capstone project **WebSentinel: An Explainable Website Security Assessment and Phishing Detection System**.

## How this paper was grounded

The current Git workspace (`cursor_repo`) is a **PII redaction tool**, not WebSentinel. Before writing, the private repository `seethinajayadileep/WebSentinel` (commit `7d8822f`, 29 August 2026) and the uploaded capstone PDF were inspected.

Nothing in this paper invents accuracy numbers, scan times, dataset sizes, or test pass rates.

## Layout

```
research-paper/
  main.tex                 Complete IEEEtran conference paper
  references.bib           BibTeX copy of the same genuine sources
  figures/
    architecture.md        Mermaid source for Fig. 1
    workflow.md            Mermaid source for Fig. 2
    ml_pipeline.md         Mermaid source for Fig. 3
    risk_scoring.md        Mermaid source for Fig. 4
  tables/
    evaluation_tables.tex  Extra / printable table templates
  README.md                This file
```

`main.tex` already embeds compact TikZ versions of the four figures so the PDF compiles without a Mermaid renderer. Convert the `.md` diagrams later if you want publication-quality drawings.

## How to compile

```bash
sudo apt-get update
sudo apt-get install -y texlive-publishers texlive-science texlive-fonts-recommended \
  texlive-latex-extra texlive-pictures
cd research-paper
pdflatex main.tex
pdflatex main.tex
```

`main.tex` uses a manual `thebibliography` so a BibTeX pass is not required. If you prefer BibTeX:

1. Replace the `thebibliography` environment with `\bibliographystyle{IEEEtran}\bibliography{references}`.
2. Run `pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex`.

Author names: Option A (all six project members) is active. Option B (research-paper team only: Ruthwik Kakumani, Somineni Venumadhava, Seethina Jaya Dileep) is commented at the top of `main.tex`. Replace the `INSERT DEPARTMENT`, `INSERT UNIVERSITY`, `INSERT CITY`, `INSERT COUNTRY`, and `INSERT EMAIL` tokens in the author block. Bracketed `[INSERT ...]` tokens were avoided there because IEEEtran treats `[...]` as an optional argument.

Compilation was verified with TeX Live 2023 / IEEEtran 1.8b (`pdflatex` twice, 11 pages, no undefined citations). The PDF is generated locally as `main.pdf` and is gitignored.

## Claims that come from implemented code

These statements are taken from `seethinajayadileep/WebSentinel`:

| Claim | Source |
|---|---|
| Chrome Manifest V3 popup, `activeTab`, host permission for the Vercel API | `frontend/manifest.json` |
| Only `scheme + hostname` (origin) is sent; path and query stay on device | `frontend/app.js`, privacy policy |
| Unsupported schemes rejected client- and server-side | `frontend/app.js`, `backend/testingmain.js` |
| Express API: `GET /health`, `POST /check`, 8 kB JSON limit | `backend/server.js` |
| HTTPS scheme check | `backend/testhttp.js` |
| TLS check via `ssl-checker`, 8 s timeout | `backend/testssl.js` |
| Domain age / registrar / DNSSEC from a WHOIS HTML scrape (`who.zmh.me`) | `backend/testdata.js` |
| Additive score weights and Safe / Suspicious / High risk bands (`<24`, `<59`) | `backend/testingmain.js` |
| `rdap.js` is an empty file | repository listing, size 0 |
| One Node one-liner test for `chrome://` rejection | `backend/package.json` |
| Vercel Node deployment | `backend/vercel.json` |
| Production endpoint `https://web-sentinel-eight.vercel.app/check` | `frontend/app.js` |
| Advisory disclaimer: a low score is not a guarantee of safety | `frontend/index.html` |

Implemented score weights (not experimentally tuned):

- Missing HTTPS: +20
- Invalid / missing TLS: +20
- Certificate expires in fewer than 7 days: +3
- Domain age < 7 days / 1 month / 6 months / 1 year: +35 / +25 / +15 / +8 (first match)
- WHOIS updated in last 7 / 30 days: +10 / +6
- HTTPS and DNSSEC reported signed: −3
- Floor at 0

## Portions that describe planned work

Do **not** present these as finished features. They come from the capstone proposal and from the architecture specified in the paper:

- React + TypeScript + Tailwind dashboard
- FastAPI backend
- PostgreSQL scan history and report storage
- Redis + Celery/RQ background jobs
- HTTPX, dnspython, real RDAP, Beautiful Soup, cryptography-based collectors
- DNS A/AAAA/MX/NS/TXT collection
- Redirect-chain analysis
- IP / hosting / geolocation
- CMS / framework / technology detection
- Approved threat-intelligence and breach APIs
- scikit-learn phishing model and SHAP explanations
- Downloadable security-assessment reports
- User authentication, saved reports, verified-domain monitoring, change alerts
- Docker, Nginx, GitHub Actions, pytest, Vitest, Playwright, OWASP ZAP
- Five-level academic risk bands (0–20 … 81–100)
- Normalized weighted model \(R=\sum w_i f_i\) as a *proposed* generalisation of the prototype

The paper states this separation in Section VI, Table II (status table), and the figure captions.

## Where experimental placeholders remain

Search `main.tex` for `[INSERT` and `[RESULT REQUIRED]` and `---`.

| Placeholder | Where |
|---|---|
| Department, university, city, country, emails | Author block |
| Acknowledgment text | Acknowledgment |
| Hardware / OS | Section VII |
| Dataset name, size, class counts, dates, split | Section VII |
| Retention policy | Section X |
| ML metrics | Table III in the paper (`tab:ml-results`) |
| Module test counts | Table IV (`tab:module-tests`) |
| Scan latency | Table V (`tab:scan-perf`) |
| Functional observed/status cells | Table VI (`tab:functional`) |

`tables/evaluation_tables.tex` repeats the same templates for copy-paste.

## Information Required Before Final Submission

Fill every item below with a real measurement or institutional fact. Do not guess.

### Institutional

1. Official department and university names
2. City and country
3. Author emails (or a single corresponding-author email)
4. Whether the author list is all six members or only the research-paper team
5. Advisor name, if required by the venue
6. Acknowledgment / funding sentence
7. Target venue name and year (update the footer if the template requires it)

### Prototype evidence you already have (optional to add as figures)

8. Screenshot of the Chrome popup on a known-good HTTPS site
9. Screenshot on an HTTP site and on a newly registered domain
10. Example JSON from `POST /check`

### Experiments that do not yet exist

11. Hardware configuration used for tests
12. Licensed phishing / legitimate dataset citation, collection dates, and counts
13. Train/test (or chronological) split
14. Trained model choice and hyperparameters
15. Accuracy, precision, recall, F1-score, ROC-AUC, confusion matrix
16. False-negative case review
17. Functional test execution log (pytest / Vitest / Playwright)
18. OWASP ZAP report against *your* deployment, not against third-party sites
19. Mean / min / max scan times by website class
20. SSRF test results after private-IP and metadata denylists are implemented
21. Data-retention policy if you add PostgreSQL
22. Confirmation that `rdap.js` was implemented, or keep the “empty file” statement

Until items 14–16 exist, leave ML result cells as `[RESULT REQUIRED]`.

## Quality checklist (already applied)

- IEEE conference structure (`IEEEtran`, numbered sections, index terms)
- IEEE numeric citations; bibliography entries are real papers, RFCs, or OWASP/APWG documents
- Citation keys in `main.tex` match `references.bib`
- No fabricated experimental numbers
- Implemented versus planned features are separated in prose and in tables
- Equations use `amsmath`
- Tables and figure captions use IEEE-style numbering
- Abstract (~180–250 words) does not claim a measured accuracy
- Conclusion does not introduce new empirical claims
- Writing is original academic English, not marketing copy
