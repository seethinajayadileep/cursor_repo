# OpenScout

Open-source **testing agent** for web apps. It runs journeys written in English (or Gherkin), explores a live UI in a real Chromium browser, reports console / network / accessibility bugs, and writes a Playwright test when a journey passes.

No LLM key is required. If you set `OPENSCOUT_LLM_API_KEY` (OpenAI-compatible), explore mode can ask the model which control to try next.

## Why this exists

Selector-based suites rot when the DOM moves. Hosted AI QA tools fix that by locking your tests and history behind a vendor. OpenScout keeps the agent, the runs, and the generated tests on your machine.

It is intentionally small: a planner, a Playwright session, detectors, and a report. You can read the whole agent in `openscout/`.

## Install

```bash
python -m pip install -r openscout/requirements.txt
python -m playwright install chromium
```

Python 3.11+ recommended.

## 60-second demo

The bundled **Harbor Kiln** shop looks like a ceramics storefront and is seeded with bugs (404 careers page, coupon API 500, console crash on Broken Mug, missing image alt, unnamed icon button, Express checkout JS exception).

```bash
# terminal 1 — demo shop
python -m openscout demo --port 8765

# terminal 2 — run a passing journey
python -m openscout run journeys/guest_checkout.feature --url http://127.0.0.1:8765

# crawl until it hits the landmines
python -m openscout explore --url http://127.0.0.1:8765 --max-steps 22
```

A dashboard (starts the demo shop on port 8765 for you):

```bash
python -m openscout serve
```

Open `http://127.0.0.1:8000`. Paste a URL, run a journey or an explore, download the HTML report under `runs/`.

## Journeys

`journeys/guest_checkout.feature`:

```gherkin
Feature: Guest checkout
  Scenario: Buy the red mug
    Given I open the home page
    When I click "Shop"
    And I click "Red Mug"
    And I click "Add to cart"
    And I fill "Full name" with "Ada Lovelace"
    And I fill "Email" with "ada@example.com"
    And I click "Place order"
    Then I should see "Order confirmed"
```

Supported steps: `open` / `go to`, `click`, `fill` / `type … into`, `select`, `check` / `uncheck`, `should see`, `should not see`, `url should contain`, `title should be`, `wait`, `screenshot`, `no console errors`.

On a passing run, OpenScout writes `generated_test.py` next to the report. Re-run generation with:

```bash
python -m openscout generate journeys/guest_checkout.feature --url http://127.0.0.1:8765 -o tests/test_guest_checkout.py
```

## Explore mode

Frontier crawl over visible buttons, links, and fields. It skips `mailto:`, logout, and other origins. Detectors record:

| Kind | What it flags |
| --- | --- |
| javascript | `pageerror` exceptions |
| console | `console.error` |
| network | HTTP 4xx / 5xx |
| a11y | images without `alt`, controls with no accessible name |
| content | nearly empty pages |

## LLM (optional)

```bash
export OPENSCOUT_LLM_API_KEY=...
export OPENSCOUT_LLM_MODEL=gpt-4o-mini          # default
export OPENSCOUT_LLM_BASE_URL=https://api.openai.com/v1
```

Any OpenAI-compatible server works (Ollama, LM Studio, OpenRouter). Without a key, a heuristic ranks controls (checkout, coupon, careers, forms first).

## Layout

```
openscout/          agent, CLI, dashboard, Harbor Kiln demo
journeys/           sample English tests
tests/              planner unit tests + Playwright runs against the demo shop
runs/               reports, screenshots, generated tests (gitignored)
```

```bash
pytest -q
```

## PII redaction tool

This repository also contains a prospectus / ticket-log redaction engine (`redact/`, `python main.py`). It is separate from OpenScout.

## License

MIT. See `LICENSE`.
