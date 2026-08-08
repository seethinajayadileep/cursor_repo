#!/usr/bin/env python3
"""
Automate Mobbin / Stripe Checkout promo-code checks.

Reads coupon codes from a text file, enters each on the checkout page,
and reports whether the code applied (working) or failed (not working).

Usage:
  python check_coupons.py --url "https://checkout.stripe.com/c/pay/cs_live_..." --file coupons.txt
  python check_coupons.py --url "..." --file coupons.txt --headed
  python check_coupons.py --url "..." --file coupons.txt --output results.txt
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright


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
    """Ensure the promotion code input is visible and focused."""
    promo = page.locator("#promotionCode, input[name='promotionCode']")
    if promo.count() and promo.first.is_visible():
        return

    # Mobile / collapsed UI: click "Add code"
    add_code = page.locator(
        '[data-testid="product-summary-promo-code"], '
        'button:has-text("Add code"), '
        'button:has-text("Add promotion code")'
    )
    if add_code.count():
        try:
            add_code.first.click(timeout=5000)
            page.wait_for_timeout(500)
        except PlaywrightTimeout:
            pass

    # Fallback: click the "Add promotion code" label/input area
    label = page.locator("text=Add promotion code")
    if label.count():
        try:
            label.first.click(timeout=3000)
        except PlaywrightTimeout:
            pass


def clear_existing_promo(page) -> None:
    """Remove a previously applied promo code if a remove/clear control exists."""
    remove_selectors = [
        'button[aria-label*="Remove" i]',
        'button[aria-label*="Clear" i]',
        'button:has-text("Remove")',
        '[data-testid*="promotion"] button',
        '.PromotionCodeEntry button[type="button"]:has(svg)',
    ]
    for sel in remove_selectors:
        btns = page.locator(sel)
        count = btns.count()
        for i in range(count):
            btn = btns.nth(i)
            try:
                if btn.is_visible():
                    label = (btn.get_attribute("aria-label") or btn.inner_text() or "").lower()
                    # Avoid clicking Apply / Legal / etc.
                    if any(k in label for k in ("remove", "clear", "delete", "×", "x")):
                        btn.click(timeout=2000)
                        page.wait_for_timeout(800)
                        return
            except Exception:
                continue


def get_total(page) -> float | None:
    selectors = [
        "#OrderDetails-TotalAmount",
        '[id="OrderDetails-TotalAmount"]',
        "#ProductSummary-totalAmount",
        '[data-testid="product-summary-total-amount"]',
        '[data-testid="order-details-footer-subtotal-amount"]',
    ]
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count():
            try:
                text = loc.first.inner_text(timeout=2000)
                amount = parse_amount(text)
                if amount is not None:
                    return amount
            except Exception:
                continue
    return None


def visible_error(page) -> str | None:
    """Return promo-related error text if present."""
    error_selectors = [
        ".FieldError",
        ".FieldError-container .Text",
        '[role="alert"]',
        ".PromotionCodeEntry .FieldError",
        "span.FieldError",
    ]
    for sel in error_selectors:
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
                # Ignore empty/zero-opacity placeholders that still have structure
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
                # Any non-empty FieldError near promo is likely a failure
                if "FieldError" in sel and len(text) > 2:
                    return text
            except Exception:
                continue
    return None


def promo_applied_indicator(page, code: str) -> bool:
    """Heuristic: applied promo chip / discount line appears."""
    code_lower = code.lower()
    candidates = [
        page.locator(f'text=/{re.escape(code)}/i'),
        page.locator('[data-testid*="promotion"]'),
        page.locator(".PromotionCodeAndDiscountLines"),
        page.locator("text=/discount/i"),
        page.locator("text=/off$/i"),
    ]
    for loc in candidates:
        try:
            if loc.count() == 0:
                continue
            for i in range(min(loc.count(), 5)):
                el = loc.nth(i)
                if not el.is_visible():
                    continue
                text = (el.inner_text() or "").strip().lower()
                if not text:
                    continue
                if code_lower in text:
                    return True
                if "discount" in text or "% off" in text or "₹" in text and "-" in text:
                    # Discount line after applying is a good signal
                    if "add promotion" not in text:
                        return True
        except Exception:
            continue
    return False


def apply_coupon(page, code: str, wait_ms: int = 3500) -> tuple[bool, str]:
    """
    Enter a coupon and decide if it worked.
    Returns (working, detail_message).
    """
    open_promo_input(page)
    clear_existing_promo(page)
    open_promo_input(page)

    promo = page.locator("#promotionCode, input[name='promotionCode']").first
    promo.wait_for(state="visible", timeout=15000)

    before_total = get_total(page)

    promo.click()
    promo.fill("")
    promo.fill(code)

    # Apply button becomes enabled after typing
    apply_btn = page.locator(
        'button:has-text("Apply"):not([disabled]), '
        '.PromotionCodeEntry button:has-text("Apply")'
    )
    # Prefer enabled Apply near the promo field
    apply_candidates = page.locator('button:has-text("Apply")')
    clicked = False
    for i in range(apply_candidates.count()):
        btn = apply_candidates.nth(i)
        try:
            if btn.is_visible() and btn.is_enabled():
                btn.click(timeout=5000)
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        # Press Enter as fallback
        promo.press("Enter")

    page.wait_for_timeout(wait_ms)

    err = visible_error(page)
    if err:
        return False, err

    after_total = get_total(page)
    if (
        before_total is not None
        and after_total is not None
        and after_total < before_total - 0.001
    ):
        return True, f"total {before_total} -> {after_total}"

    if promo_applied_indicator(page, code):
        return True, "promo applied (UI indicator)"

    # Input cleared / replaced by applied badge is often success
    try:
        value = promo.input_value()
        if value.strip() == "" and promo_applied_indicator(page, code):
            return True, "promo applied"
    except Exception:
        pass

    # If Apply stayed disabled or nothing changed, treat as not working
    if before_total is not None and after_total is not None and after_total == before_total:
        # Double-check for success chip with the code text in order details footer
        footer = page.locator(".OrderDetails-footer, .YGErOEoF__Subtotal, .FadeWrapper")
        try:
            footer_text = footer.inner_text(timeout=2000).lower()
            if code.lower() in footer_text and "add promotion" not in footer_text:
                return True, "code visible in order details"
        except Exception:
            pass
        return False, "no discount / total unchanged"

    return False, "could not confirm application"


def run(url: str, coupons: list[str], headed: bool, slow_mo: int, output: Path | None) -> int:
    results: list[tuple[str, bool, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, slow_mo=slow_mo or 0)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()
        print(f"Opening checkout: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait for Stripe checkout shell
        try:
            page.wait_for_selector(
                "#promotionCode, input[name='promotionCode'], "
                '[data-testid="product-summary-promo-code"], '
                '[data-testid="checkout-container"]',
                timeout=45000,
            )
        except PlaywrightTimeout:
            print("ERROR: Checkout page did not load expected elements.", file=sys.stderr)
            browser.close()
            return 2

        # Extra settle time for Stripe JS
        page.wait_for_timeout(2000)

        for idx, code in enumerate(coupons, start=1):
            print(f"[{idx}/{len(coupons)}] Trying: {code} ... ", end="", flush=True)
            try:
                working, detail = apply_coupon(page, code)
            except Exception as exc:
                working, detail = False, f"error: {exc}"

            status = "working" if working else "not working"
            print(f"{status} ({detail})")
            results.append((code, working, detail))

            # Brief pause between attempts; refresh if page looks stuck
            page.wait_for_timeout(600)

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
        description="Test promo/coupon codes on a Mobbin Stripe Checkout page."
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Stripe Checkout URL (e.g. https://checkout.stripe.com/c/pay/cs_live_...)",
    )
    parser.add_argument(
        "--file",
        "-f",
        default="coupons.txt",
        help="Text file with one coupon per line (default: coupons.txt)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Optional path to write TSV results",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window (useful for debugging)",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=0,
        help="Slow down Playwright actions by N ms",
    )
    args = parser.parse_args()

    coupons_path = Path(args.file)
    if not coupons_path.exists():
        print(f"ERROR: coupons file not found: {coupons_path}", file=sys.stderr)
        return 1

    coupons = load_coupons(coupons_path)
    if not coupons:
        print(f"ERROR: no coupons found in {coupons_path}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else None
    return run(args.url, coupons, args.headed, args.slow_mo, output)


if __name__ == "__main__":
    raise SystemExit(main())
