# PII Redaction Evaluation Report

## Evaluation approach

The sample Red Herring Prospectus (with an investor ticket-log appendix) is generated from a labeled fixture in `sample_data.py`. That fixture is the gold standard: every name, email, phone, company, address, SSN, credit card, date of birth, and IP is known before the redactor runs.

**Scope choice:** Ticket IDs (`TKT-*`), Order IDs (`ORD-*`), application numbers (`APP-*`), the CIN, regulator names (SEBI), and corporate event dates (prospectus date, incorporation date) are **not** treated as PII. They are the true-negative set.

Matching is entity-level exact match on `(pii_type, value)` after whitespace normalization. Occurrence recall is a second check: gold strings must not remain in the redacted .docx.

- Source: `data/red_herring_prospectus.docx`
- Output: `output/redacted_prospectus.docx`
- Gold unique entities: 33
- Detected unique entities: 33

## Overall metrics

| Metric | Value |
| --- | --- |
| True positives | 33 |
| False positives | 0 |
| False negatives | 0 |
| True negatives (kept operational IDs) | 20 |
| **Precision** | **100.0%** |
| **Recall** | **100.0%** |
| F1 | 100.0% |
| **Accuracy** | **100.0%** |
| Occurrence leak check (gold still in output) | 0 leftover |

## Metrics by PII type

| Type | Gold | TP | FP | FN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| address | 6 | 6 | 0 | 0 | 100.0% | 100.0% |
| company | 3 | 3 | 0 | 0 | 100.0% | 100.0% |
| credit_card | 2 | 2 | 0 | 0 | 100.0% | 100.0% |
| date_of_birth | 4 | 4 | 0 | 0 | 100.0% | 100.0% |
| email | 4 | 4 | 0 | 0 | 100.0% | 100.0% |
| ip_address | 4 | 4 | 0 | 0 | 100.0% | 100.0% |
| name | 4 | 4 | 0 | 0 | 100.0% | 100.0% |
| phone | 4 | 4 | 0 | 0 | 100.0% | 100.0% |
| ssn | 2 | 2 | 0 | 0 | 100.0% | 100.0% |

## False positives

None.

## False negatives

None.

## Non-PII preservation

Preserved 20 / 20 operational identifiers and corporate facts.

All ticket, order, CIN, and corporate-fact strings remain in the redacted file.

## Replacement counts (occurrences, including repeats)

| Type | Replacements |
| --- | ---: |
| address | 10 |
| company | 5 |
| credit_card | 2 |
| date_of_birth | 8 |
| email | 9 |
| ip_address | 4 |
| name | 18 |
| phone | 9 |
| ssn | 2 |

## Notes

- These figures are measured on the labeled sample prospectus (33 unique PII entities, 20 true-negative operational IDs). They are not a claim of 100% performance on an arbitrary 400-page commercial RHP.
- Dates of birth are redacted only when anchored by `Date of Birth` / `DOB` / `born on`, so filing dates such as August 13, 2026 are kept.
- Credit cards require a Luhn checksum so long digit strings that are not card numbers are not redacted.
- Person names use Title-Case matching plus a stopword list; a gazetteer/NER model would catch rarer names at the cost of more code and more false positives on headings.
- Websites/domains (for example `www.novatechanalytics.example`) are left intact; only email addresses are redacted.

