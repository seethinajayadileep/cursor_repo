#!/usr/bin/env python3
"""
Automate Mobbin / Stripe Checkout promo-code checks.

Edit the CONFIG variables below, then run:
  python check_coupons.py

Optional CLI overrides still work:
  python check_coupons.py --url "..." --file coupons.txt --headed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

# =============================================================================
# CONFIG — edit these values
# =============================================================================
URL = "https://checkout.stripe.com/c/pay/cs_live_PASTE_YOUR_FRESH_SESSION_HERE"
FILE = "coupons.txt"          # text file with one promo code per line
OUTPUT = ""                   # e.g. "results.txt" (leave empty to skip)
HEADED = False                # True = show browser window
SLOW_MO = 0                   # slow Playwright actions by N ms (0 = off)
# =============================================================================

PROMO_INPUT = "#promotionCode, input[name='promotionCode']"
APPLY_BTN = 'button[class*="PromotionCodeEntry-applyButton"], button:has-text("Apply")'
REMOVE_BTN = (
    'button[class*="AppliedDiscount-removeButton"], '
    '[class*="AppliedDiscount"] button, '
    'button[aria-label*="Remove" i], '
    'button[aria-label*="Clear" i]'
)
APPLIED = '[class*="AppliedDiscount"]'


def load_coupons(path: Path) -> list[str]:
    codes: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        codes.append(line)
    return codes


def parse_amount(text: str) -> float | None:
    """Extract a numeric amount from currency text like '₹9,600.00' or '$96.00'."""
    cleaned = text.replace(",", "").replace("\u00a0", " ")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None
    return float(match.group(1))


def open_promo_input(page) -> None:
    """Ensure the promotion code input is visible."""
    promo = page.locator(PROMO_INPUT)
    if promo.count() and promo.first.is_visible():
        return

    add_code = page.locator(
        '[data-testid="product-summary-promo-code"], '
        'button:has-text("Add code"), '
        'button:has-text("Add promotion code"), '
        "text=Add promotion code"
    )
    for i in range(add_code.count()):
        try:
            el = add_code.nth(i)
            if el.is_visible():
                el.click(timeout=4000)
                page.wait_for_timeout(600)
                break
        except Exception:
            continue


def clear_existing_promo(page) -> bool:
    """Remove a previously applied promo. Returns True if a remove was clicked."""
    removed = False
    for _ in range(3):
        btns = page.locator(REMOVE_BTN)
        clicked = False
        for i in range(btns.count()):
            btn = btns.nth(i)
            try:
                if not btn.is_visible():
                    continue
                cls = (btn.get_attribute("class") or "").lower()
                aria = (btn.get_attribute("aria-label") or "").lower()
                text = (btn.inner_text() or "").lower()
                label = f"{cls} {aria} {text}"
                if "apply" in label and "remove" not in label:
                    continue
                if any(k in label for k in ("remove", "clear", "delete", "applieddiscount")):
                    btn.click(timeout=3000)
                    page.wait_for_timeout(1200)
                    removed = True
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            break
    return removed


def get_total_due_today(page) -> float | None:
    """Read Total due today only — never the always-unchanged subtotal."""
    # Primary: dedicated total amount node
    loc = page.locator("#OrderDetails-TotalAmount")
    if loc.count():
        try:
            text = loc.first.inner_text(timeout=1500)
            # Prefer the first money-looking line
            for line in text.splitlines():
                if "₹" in line or "$" in line or "€" in line or re.search(r"\d", line):
                    amount = parse_amount(line)
                    if amount is not None:
                        return amount
            return parse_amount(text)
        except Exception:
            pass

    # Fallback: product summary total (may include "per year" — still ok for deltas)
    loc = page.locator('#ProductSummary-totalAmount, [data-testid="product-summary-total-amount"]')
    if loc.count():
        try:
            return parse_amount(loc.first.inner_text(timeout=1500))
        except Exception:
            pass
    return None


def visible_promo_error(page) -> str | None:
    """Return visible promo-field error text if present."""
    selectors = [
        ".PromotionCodeEntry .FieldError",
        '[class*="PromotionCodeEntry"] .FieldError',
        ".FieldError",
        '[role="alert"]',
    ]
    for sel in selectors:
        locs = page.locator(sel)
        for i in range(locs.count()):
            el = locs.nth(i)
            try:
                if not el.is_visible():
                    continue
                text = el.inner_text().strip()
                if not text:
                    continue
                lower = text.lower()
                if any(
                    k in lower
                    for k in (
                        "invalid",
                        "expired",
                        "not apply",
                        "doesn't apply",
                        "does not apply",
                        "promotion code",
                        "promo code",
                        "coupon",
                        "not valid",
                        "couldn't",
                        "could not",
                        "unable",
                    )
                ):
                    return text
            except Exception:
                continue
    return None


def applied_discount_info(page) -> dict:
    """Return info about an applied discount block, if any."""
    info = page.evaluate(
        """() => {
          const blocks = [...document.querySelectorAll('[class*="AppliedDiscount"]')];
          const texts = blocks
            .map(el => (el.innerText || '').replace(/\\s+/g, ' ').trim())
            .filter(Boolean);
          const order = document.querySelector('[data-testid="order-details"]');
          const orderText = order ? (order.innerText || '').replace(/\\s+/g, ' ').trim() : '';
          const hasRemove = !!document.querySelector('button[class*="AppliedDiscount-removeButton"]');
          const hasOff = /off for/i.test(orderText) || /-\\s*₹/.test(orderText) || /-\\s*\\$/.test(orderText);
          return { texts, orderText, hasRemove, hasOff };
        }"""
    )
    return info


def promo_is_applied(page, code: str) -> tuple[bool, str]:
    """Detect a successfully applied promo via UI."""
    code_lower = code.lower()
    info = applied_discount_info(page)

    for text in info.get("texts") or []:
        low = text.lower()
        if code_lower in low:
            return True, f"applied discount UI shows {code}"
        if "off" in low or "-" in text:
            return True, f"applied discount UI: {text[:80]}"

    order = (info.get("orderText") or "").lower()
    if code_lower in order and "add promotion" not in order and "invalid" not in order:
        # Code shown in order details outside the input
        if info.get("hasRemove") or info.get("hasOff"):
            return True, "code visible with discount in order details"

    if info.get("hasRemove") and info.get("hasOff"):
        return True, "discount line + remove control present"

    # Input gone after apply + discount present
    promo = page.locator(PROMO_INPUT)
    input_visible = bool(promo.count() and promo.first.is_visible())
    if not input_visible and (info.get("hasRemove") or info.get("hasOff")):
        return True, "promo input replaced by applied discount"

    return False, ""


def is_payment_pages_update(response) -> bool:
    """Stripe Checkout promo apply hits POST /v1/payment_pages/cs_..."""
    try:
        if response.request.method != "POST":
            return False
        url = response.url
        if "api.stripe.com/v1/payment_pages/" not in url:
            return False
        # ignore /init
        if url.rstrip("/").endswith("/init"):
            return False
        return True
    except Exception:
        return False


def enter_code(page, code: str) -> None:
    """Type a promo code so React state updates and Apply enables."""
    open_promo_input(page)
    promo = page.locator(PROMO_INPUT).first
    promo.wait_for(state="visible", timeout=15000)
    promo.click()
    # Clear existing value
    promo.fill("")
    page.wait_for_timeout(100)
    # type() fires key events; more reliable than fill() for Stripe React inputs
    promo.type(code, delay=25)
    page.wait_for_timeout(200)

    # Wait until Apply enables
    try:
        page.wait_for_function(
            """() => {
              const buttons = [...document.querySelectorAll('button')];
              return buttons.some(b => {
                const cls = b.className || '';
                const text = (b.innerText || '').trim();
                const isApply = cls.includes('PromotionCodeEntry-applyButton') || text === 'Apply';
                return isApply && !b.disabled && b.offsetParent !== null;
              });
            }""",
            timeout=8000,
        )
    except PlaywrightTimeout:
        pass


def click_apply(page) -> None:
    apply_btns = page.locator(APPLY_BTN)
    for i in range(apply_btns.count()):
        btn = apply_btns.nth(i)
        try:
            if btn.is_visible() and btn.is_enabled():
                btn.click(timeout=5000)
                return
        except Exception:
            continue
    # Fallback
    page.locator(PROMO_INPUT).first.press("Enter")


def classify_stripe_response(response) -> tuple[str, str]:
    """
    Returns (status, detail) where status is 'working', 'not_working', or 'unknown'.
    """
    try:
        status = response.status
        body = response.text()
    except Exception as exc:
        return "unknown", f"response read error: {exc}"

    if status == 200:
        # Confirm JSON looks like an updated payment page (not an error object)
        try:
            data = json.loads(body)
            if isinstance(data, dict) and data.get("error"):
                msg = data["error"].get("message") or str(data["error"])
                return "not_working", msg
        except Exception:
            pass
        return "working", f"stripe payment_pages HTTP {status}"

    # 4xx = rejected promo (or other update error)
    msg = ""
    try:
        data = json.loads(body)
        err = data.get("error") or {}
        msg = err.get("message") or err.get("code") or ""
        # Sometimes message is nested
        if not msg and isinstance(err, dict):
            msg = json.dumps(err)[:200]
    except Exception:
        msg = body[:200] if body else ""

    if status >= 400:
        return "not_working", msg or f"stripe HTTP {status}"
    return "unknown", f"stripe HTTP {status}"


def apply_coupon(page, code: str) -> tuple[bool, str]:
    """
    Enter a coupon and decide if it worked.
    Returns (working, detail_message).
    """
    clear_existing_promo(page)
    open_promo_input(page)

    before_total = get_total_due_today(page)
    enter_code(page, code)

    api_result: tuple[str, str] | None = None
    try:
        with page.expect_response(is_payment_pages_update, timeout=15000) as resp_info:
            click_apply(page)
        api_result = classify_stripe_response(resp_info.value)
    except PlaywrightTimeout:
        # No payment_pages POST seen — fall through to UI checks
        page.wait_for_timeout(2000)
    except Exception:
        page.wait_for_timeout(2000)

    # Let UI settle after the network response
    page.wait_for_timeout(800)

    # 1) Prefer Stripe API outcome
    if api_result is not None:
        status, detail = api_result
        if status == "working":
            ok, ui_detail = promo_is_applied(page, code)
            after = get_total_due_today(page)
            if ok:
                return True, ui_detail
            if (
                before_total is not None
                and after is not None
                and after < before_total - 0.001
            ):
                return True, f"total {before_total} -> {after}"
            return True, detail
        if status == "not_working":
            err = visible_promo_error(page)
            return False, err or detail or "rejected by Stripe"

    # 2) UI error
    err = visible_promo_error(page)
    if err:
        return False, err

    # 3) UI applied indicators
    ok, detail = promo_is_applied(page, code)
    if ok:
        return True, detail

    # 4) Total dropped
    after_total = get_total_due_today(page)
    if (
        before_total is not None
        and after_total is not None
        and after_total < before_total - 0.001
    ):
        return True, f"total {before_total} -> {after_total}"

    if before_total is not None and after_total is not None and after_total == before_total:
        return False, "no discount / total unchanged"

    return False, "could not confirm application"


def run(url: str, coupons: list[str], headed: bool, slow_mo: int, output: Path | None) -> int:
    results: list[tuple[str, bool, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, slow_mo=slow_mo or 0)
        context = browser.new_context(
            viewport={"width": 1400, "height": 1000},
            locale="en-IN",
        )
        page = context.new_page()
        print(f"Opening checkout: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        try:
            page.wait_for_selector(
                f"{PROMO_INPUT}, {APPLIED}, "
                '[data-testid="product-summary-promo-code"], '
                '[data-testid="checkout-container"]',
                timeout=45000,
            )
        except PlaywrightTimeout:
            print("ERROR: Checkout page did not load expected elements.", file=sys.stderr)
            browser.close()
            return 2

        page.wait_for_timeout(2000)
        # If session already has a code, clear it so totals/baseline are clean
        clear_existing_promo(page)
        open_promo_input(page)

        for idx, code in enumerate(coupons, start=1):
            print(f"[{idx}/{len(coupons)}] Trying: {code} ... ", end="", flush=True)
            try:
                working, detail = apply_coupon(page, code)
            except Exception as exc:
                working, detail = False, f"error: {exc}"

            status = "working" if working else "not working"
            print(f"{status} ({detail})")
            results.append((code, working, detail))
            page.wait_for_timeout(400)

        browser.close()

    print("\n=== Summary ===")
    working_codes = [c for c, ok, _ in results if ok]
    failed_codes = [c for c, ok, _ in results if not ok]
    for code, ok, detail in results:
        print(f"{'WORKING' if ok else 'NOT WORKING':12}  {code}  — {detail}")

    print(f"\nWorking: {len(working_codes)} / {len(results)}")
    if working_codes:
        print("Working codes:", ", ".join(working_codes))
    if failed_codes:
        print("Not working:", ", ".join(failed_codes))

    if output:
        lines = []
        for code, ok, detail in results:
            lines.append(f"{'working' if ok else 'not working'}\t{code}\t{detail}")
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWrote results to {output}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test promo/coupon codes on a Mobbin Stripe Checkout page. "
        "Edit URL/FILE at the top of this script, or pass CLI flags."
    )
    parser.add_argument("--url", default=None, help="Stripe Checkout URL (overrides URL)")
    parser.add_argument("--file", "-f", default=None, help="Coupons file (overrides FILE)")
    parser.add_argument("--output", "-o", default=None, help="TSV results path (overrides OUTPUT)")
    parser.add_argument(
        "--headed",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show/hide browser window (overrides HEADED)",
    )
    parser.add_argument("--slow-mo", type=int, default=None, help="Slow actions by N ms")
    args = parser.parse_args()

    url = args.url if args.url is not None else URL
    file_name = args.file if args.file is not None else FILE
    output_name = args.output if args.output is not None else OUTPUT
    headed = args.headed if args.headed is not None else HEADED
    slow_mo = args.slow_mo if args.slow_mo is not None else SLOW_MO

    if not url or "PASTE_YOUR_FRESH_SESSION_HERE" in url:
        print("ERROR: set URL at the top of check_coupons.py (or pass --url).", file=sys.stderr)
        return 1

    coupons_path = Path(file_name)
    if not coupons_path.exists():
        print(f"ERROR: coupons file not found: {coupons_path}", file=sys.stderr)
        return 1

    coupons = load_coupons(coupons_path)
    if not coupons:
        print(f"ERROR: no coupons found in {coupons_path}", file=sys.stderr)
        return 1

    output = Path(output_name) if output_name else None
    return run(url, coupons, headed, slow_mo, output)


if __name__ == "__main__":
    raise SystemExit(main())
