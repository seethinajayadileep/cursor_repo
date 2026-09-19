# Partner perk catalog

Extracted from `partner-perk-pages-MASTER.csv` by fetching live perk URLs.

| File | What it is |
| --- | --- |
| `UNIQUE_PERKS.md` | Readable catalog of unique vendor perks and typical terms |
| `unique_perks_clean.csv` | Same catalog as a table |
| `unique_perks.csv` | Raw extractor output (vendors + noisy observed strings) |
| `stats.json` | Fetch coverage |

Regenerate:

```bash
python3 scripts/extract_unique_perks.py
python3 scripts/generate_perk_report.py
```
