# PII Redaction Tool

Python regex redactor that reads a Red Herring Prospectus `.docx` (plus its ticket-log appendix) and writes a redacted `.docx`. Each detected value is replaced with a **stable fake alternative** (for example `Rashi Patil` → `John Doe`, `rashhi.patil@gmail.com` → `john.doe@example.com`), not a black bar.

**Approach:** `python-docx` for I/O, regular expressions (plus Luhn for cards) for detection, and Faker for fakes. No NER model — that keeps the code short and easy to explain. Ticket / order / CIN / application numbers are **not** treated as PII.

The attached prospectus was not in the repository, so `build_sample.py` writes a short Red Herring Prospectus `.docx` with a ticket-log appendix that covers every required PII type (including the brief's Rashi Patil / Rohan Dey examples).

**Tradeoffs:** Structured types (email, phone, SSN, card, IP, labeled DOB) are high-precision. Names and companies depend on Title-Case + legal suffixes and can miss unusual names or over-redact heading-like phrases; a stopword list limits that. Filing dates and ticket/order/CIN numbers are kept. Websites are not redacted.

**Sample metrics:** precision **100%**, recall **100%**, accuracy **100%** on 33 labeled entities (see `output/evaluation_report.md`). That is fixture performance, not a claim about a full commercial RHP.

```bash
pip install -r requirements.txt
python build_sample.py
python redact.py data/red_herring_prospectus.docx -o output/redacted_prospectus.docx --log output/redaction_log.json
python evaluate.py
pytest -q
```

To add a PII type, append one `(name, find_fn)` pair to `DETECTORS` in `redact.py` and a branch in `Redactor._generate`.
