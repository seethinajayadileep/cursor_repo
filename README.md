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

Stripe Checkout session URLs expire quickly. Open Mobbin → start checkout → copy the live `checkout.stripe.com` URL, then:

```bash
python check_coupons.py \
  --url "https://checkout.stripe.com/c/pay/cs_live_YOUR_SESSION_ID" \
  --file coupons.txt \
  --output results.txt
```

Debug with a visible browser:

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
- A code is **working** if the total drops, a discount/promo chip appears, or the code shows as applied.
- A code is **not working** if Stripe shows an error or the total does not change.
- Do not commit live payment cards or secrets. Session URLs are temporary.
