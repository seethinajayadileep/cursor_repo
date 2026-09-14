# WebSentinel IEEE Research Paper

**Title:** WebSentinel: An Explainable Website Security Assessment Framework for Phishing Risk Analysis

This directory contains an IEEE conference paper for the WebSentinel capstone. The paper distinguishes the **implemented Chrome-extension prototype** from the **proposed later architecture**. It does not invent accuracies, dataset sizes, or scan times.

See `FINAL_REVIEW.md` for the latest polish pass.

## Layout

```
research-paper/
  main.tex                 IEEEtran conference paper
  main.pdf                 Compiled PDF (regenerate after edits)
  references.bib           Genuine BibTeX sources
  FINAL_REVIEW.md          Change log and remaining manual items
  figures/                 Mermaid sources for later drawing
  tables/evaluation_tables.tex   Metric templates (not compiled until measured)
  README.md
```

## How to compile

BibTeX is required. A PDF compiled with only `pdflatex` will show `[?]` citations.

```bash
cd research-paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Or:

```bash
latexmk -pdf main.tex
```

Required packages: `texlive-publishers`, `texlive-science`, `texlive-latex-extra`, `texlive-pictures`, `texlive-fonts-recommended`.

## Author block

Option A (default): all six project members.
Option B (commented): Ruthwik Kakumani, Somineni Venumadhava, Seethina Jaya Dileep.

Set affiliation macros at the top of `main.tex` (`\WSDept`, `\WSUniv`, `\WSCity`, `\WSCountry`, `\WSEmail`) before camera-ready submission. Do not invent institutional names.

## Implemented versus planned

Implemented (inspected `seethinajayadileep/WebSentinel`, commit `7d8822f`): Chrome popup, Express `/check`, HTTPS, TLS, WHOIS age, rule score, reason list, origin-only transmission.

Planned: FastAPI, React, PostgreSQL, Redis, RDAP, DNS, redirects, technologies, threat intel, ML, SHAP, auth, history, reports, monitoring, production SSRF guards, Docker/CI.

## Get the PDF on your computer

From this branch:

```bash
git clone -b cursor/websentinel-research-paper-2d34 https://github.com/seethinajayadileep/cursor_repo.git
cd cursor_repo/research-paper
```

Open `main.pdf`, or recompile as above.
