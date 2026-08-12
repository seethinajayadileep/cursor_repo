# Mystery HTTP — recon toolkit drill

Undocumented practice API plus a boring-on-purpose HTTP client toolkit.

## Files

| File | Role |
|---|---|
| `mystery_api.py` | Practice server (stdlib only). Three levels. |
| `http_toolkit.py` | Reusable client: probe, discover, paginate, crawl, 429 backoff. |
| `solve.py` | Clears all three levels using the toolkit. |

## Run

```bash
# terminal 1
python3 mystery_api.py

# terminal 2
python3 solve.py
# or explore manually:
python3 http_toolkit.py
```

Stuck after a genuine attempt: `python3 mystery_api.py --spoilers`

## What the levels teach

1. **Discovery + auth** — follow `X-Hint` / `Link` / `WWW-Authenticate`; 422 bodies are the schema.
2. **Pagination + rate limits** — honour `Link: rel="next"`, `X-Total-Count`, and `Retry-After`.
3. **Graph traversal** — BFS linked resources; decoys have `seq == 0`; order by `seq` and concatenate payloads.
