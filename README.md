# Mobbin Stripe Coupon Checker

Python automation that reads promo codes from a text file, enters each on a Mobbin Stripe Checkout page, and reports whether the code applied (**working**) or not (**not working**).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Coupons file

Put one code per line in `coupons.txt` (or any file you pass with `--file`):

```text
SAVE20
WELCOME10
# comments are ignored
PRO50
```

## Run

Edit the CONFIG block at the top of `check_coupons.py`:

```python
URL = "https://checkout.stripe.com/c/pay/cs_live_YOUR_SESSION_ID"
FILE = "coupons.txt"
OUTPUT = "results.txt"   # or "" to skip
HEADED = False
SLOW_MO = 0
```

Stripe Checkout session URLs expire quickly. Open Mobbin → start checkout → paste a fresh URL into `URL`, then:

```bash
python check_coupons.py
```

CLI flags still override the script variables if you prefer:

```bash
python check_coupons.py --url "..." --file coupons.txt --headed --slow-mo 200
```

## Output

Console summary plus optional TSV (`results.txt`):

```text
working     SAVE20   total 9600.0 -> 7680.0
not working WELCOME10  Invalid promotion code
```

## Notes

- Uses Playwright against the real Stripe Checkout UI (`#promotionCode` + Apply).
- Detection waits for Stripe’s `payment_pages` API response (HTTP 200 = working, 4xx = not working), then confirms the Applied Discount UI / total change.
- Types codes with key events so the Apply button enables reliably; removes an already-applied code before the next attempt.
- Do not commit live payment cards or secrets. Session URLs are temporary.
