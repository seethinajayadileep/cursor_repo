# PII Redaction Tool

This repository also includes **Cursor Pocket**, a phone remote for Cursor CLI on a MacBook (same Wi-Fi, or `--online`). Mac + Android walkthrough: [MACBOOK_ANDROID.md](MACBOOK_ANDROID.md).

---

Python tool that reads the attached KSH International Red Herring Prospectus (or any PDF / ticket-log text file), finds personally identifiable information, replaces each value with a **stable fake stand-in**, and writes a redacted `.docx`.

## Approach

Hybrid **regex + gazetteer**, not a neural NER model.

| PII type | How it is found |
|---|---|
| Email, phone, SSN, credit card, IP, DOB | Regular expressions (Luhn check on cards; DOB only next to “DOB” / “born”) |
| Person names | Gazetteer of people in this prospectus, plus `Contact Person:` lines |
| Company / trust names | Gazetteer plus `Limited` / `LLP` / `Family Trust` patterns, with stopwords so headings like “Book Built Offer” are not swallowed |
| Addresses | Gazetteer of known offices plus PIN / street patterns |

The same real string always maps to the same fake value (`Faker` seeded from a hash of the original). CIN, PAN, DIN, rupee amounts, share counts, page numbers, and statute names are **not** treated as PII.

## Tradeoffs

- High precision on structured types; names/companies need the gazetteer for this legal PDF because generic Title-Case matching false-positives on “Fresh Issue” and “Equity Shares”.
- A new person who is not in `data/gazetteer.json` and not on a `Contact Person:` line can be missed (false negative).
- Address regexes can run long or short vs the gold span; evaluation allows containment matches of 10+ characters.
- SSN / card / DOB / IP do not appear in the RHP; they are scored on a synthetic ticket-log snippet.

## Run

```bash
pip install -r requirements.txt
python main.py samples/Red_Herring_Prospectus.pdf -o output/KSH_RHP_redacted.docx --evaluate
```

UI (optional wrapper around the same engine):

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`, upload the PDF, download the `.docx` and evaluation report.

## Layout

- `redact/` — extract, detect, replace, write, evaluate
- `data/gazetteer.json` — names, companies, addresses for this document
- `data/gold_labels.json` — hand labels for pages 1, 5, 6, 39 plus a synthetic ticket
- `evaluation_report.md` — precision, recall, accuracy

To add a PII type: write a detector in `detectors.py`, a fake generator in `replacements.py`, and gold examples in `gold_labels.json`.
