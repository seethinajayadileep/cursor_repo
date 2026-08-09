# Mobbin Stripe Coupon Checker

Python automation that reads promo codes from a text file, enters each on a Mobbin Stripe Checkout page, and reports whether the code applied (**working**) or not (**not working**).

## Important

Stripe rejects promo codes from Playwright’s built-in / headless browser (`This code is invalid` for every code).  
This script launches **real Google Chrome** (visible window) and controls it over CDP.

## Setup

1. Install [Google Chrome](https://www.google.com/chrome/)
2. Python deps:

```bash
pip install -r requirements.txt
python3 -m playwright install chromium
```

(`playwright` is still used as the CDP client; Chrome itself must be installed separately.)

Optional: set `CHROME_PATH` if Chrome is not on your PATH.

## Coupons file

Put one code per line in `coupons.txt`:

```text
WYU9RPJ9
E3LKRRJC
# comments are ignored
IVQXOQCM
```

## Run

Edit the CONFIG block at the top of `check_coupons.py`:

```python
URL = "https://checkout.stripe.com/c/pay/cs_live_YOUR_SESSION_ID"
FILE = "coupons.txt"
OUTPUT = "results.txt"
HEADED = True   # keep True — Stripe blocks headless
```

Stripe Checkout session URLs expire quickly. Open Mobbin → start checkout → paste a fresh URL into `URL`, then:

```bash
python check_coupons.py
```

A Chrome window will open and test each code.

## Output

```text
[1/4] Trying: WYU9RPJ9 ... working (applied discount UI shows WYU9RPJ9)
[2/4] Trying: E3LKRRJC ... working (applied discount UI shows E3LKRRJC)
[3/4] Trying: IVQXOQCM ... working (applied discount UI shows IVQXOQCM)
[4/4] Trying: AOPUCVUT ... not working (This code is invalid.)
```

## Notes

- Detection uses Stripe’s `payment_pages` API response plus the Applied Discount UI.
- Keep `HEADED = True`. Headless Chrome is blocked by Stripe for promos.
- Do not commit live payment cards or secrets. Session URLs are temporary.
