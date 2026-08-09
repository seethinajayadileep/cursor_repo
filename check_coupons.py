#!/usr/bin/env python3
"""
Automate Mobbin / Stripe Checkout promo-code checks.

IMPORTANT: Stripe rejects promos from Playwright's built-in browser / headless
Chrome. This script launches real Google Chrome (visible window) and controls
it over CDP so valid codes are accepted.

Edit the CONFIG variables below, then run:
  python check_coupons.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

# =============================================================================
# CONFIG — edit these values
# =============================================================================
URL = "https://checkout.stripe.com/c/pay/cs_live_PASTE_YOUR_FRESH_SESSION_HERE"
FILE = "coupons.txt"          # text file with one promo code per line
OUTPUT = "results.txt"        # e.g. "results.txt" (leave empty to skip)
HEADED = True                 # must stay True — Stripe blocks headless Chrome
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
    cleaned = text.replace(",", "").replace("\u00a0", " ")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None
    return float(match.group(1))


def find_chrome_binary() -> str | None:
    env = os.environ.get("CHROME_PATH") or os.environ.get("GOOGLE_CHROME_BIN")
    if env and Path(env).exists():
        return env

    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chrome",
        "chromium",
        "chromium-browser",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/local/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for_cdp(port: int, timeout_s: float = 20.0) -> str:
    url = f"http://127.0.0.1:{port}/json/version"
    deadline = time.time() + timeout_s
    last_err = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("webSocketDebuggerUrl") or f"http://127.0.0.1:{port}"
        except Exception as exc:
            last_err = exc
            time.sleep(0.2)
    raise RuntimeError(f"Chrome CDP not ready on port {port}: {last_err}")


class ChromeCDP:
    """Launch real Chrome and expose a CDP HTTP endpoint for Playwright."""

    def __init__(self, headed: bool = True):
        self.headed = headed
        self.port = free_port()
        self.proc: subprocess.Popen | None = None
        self.user_data_dir = tempfile.mkdtemp(prefix="mobbin-chrome-")
        self.cdp_url = f"http://127.0.0.1:{self.port}"

    def start(self) -> str:
        chrome = find_chrome_binary()
        if not chrome:
            raise RuntimeError(
                "Google Chrome not found. Install Chrome, or set CHROME_PATH "
                "to the chrome executable."
            )
        if not self.headed:
            print(
                "WARNING: HEADED=False often makes Stripe reject ALL promo codes. "
                "Use HEADED=True.",
                file=sys.stderr,
            )

        args = [
            chrome,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=Translate,MediaRouter",
            "--window-size=1400,1000",
            "about:blank",
        ]
        if not self.headed:
            args.insert(1, "--headless=new")

        # On Linux CI without a display, try to use existing DISPLAY.
        env = os.environ.copy()
        # start_new_session avoids Playwright/parent signal quirks; keep a real
        # headed Chrome (Stripe rejects HeadlessChrome / automated Chromium).
        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
        wait_for_cdp(self.port)
        print(f"Launched Chrome via CDP on {self.cdp_url}")
        return self.cdp_url

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        try:
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
        except Exception:
            pass


def open_promo_input(page) -> None:
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
                    try:
                        with page.expect_response(is_payment_pages_update, timeout=12000):
                            btn.click(timeout=3000)
                    except Exception:
                        try:
                            btn.click(timeout=3000)
                        except Exception:
                            continue
                    page.wait_for_timeout(1500)
                    removed = True
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            break
    # After remove, Stripe collapses the field — reopen for the next code.
    open_promo_input(page)
    return removed


def get_total_due_today(page) -> float | None:
    loc = page.locator("#OrderDetails-TotalAmount")
    if loc.count():
        try:
            text = loc.first.inner_text(timeout=1500)
            for line in text.splitlines():
                if "₹" in line or "$" in line or "€" in line or re.search(r"\d", line):
                    amount = parse_amount(line)
                    if amount is not None:
                        return amount
            return parse_amount(text)
        except Exception:
            pass
    loc = page.locator('#ProductSummary-totalAmount, [data-testid="product-summary-total-amount"]')
    if loc.count():
        try:
            return parse_amount(loc.first.inner_text(timeout=1500))
        except Exception:
            pass
    return None


def visible_promo_error(page) -> str | None:
    # Stripe sometimes puts the error next to Apply in order details text
    order = page.locator('[data-testid="order-details"]')
    if order.count():
        try:
            text = order.first.inner_text(timeout=1000)
            for line in text.splitlines():
                low = line.strip().lower()
                if "invalid" in low or "cannot be redeemed" in low or "unredeemable" in low:
                    return line.strip()
        except Exception:
            pass

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
                        "redeem",
                    )
                ):
                    return text
            except Exception:
                continue
    return None


def applied_discount_info(page) -> dict:
    return page.evaluate(
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


def promo_is_applied(page, code: str) -> tuple[bool, str]:
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
        if info.get("hasRemove") or info.get("hasOff"):
            return True, "code visible with discount in order details"
    if info.get("hasRemove") and info.get("hasOff"):
        return True, "discount line + remove control present"
    promo = page.locator(PROMO_INPUT)
    input_visible = bool(promo.count() and promo.first.is_visible())
    if not input_visible and (info.get("hasRemove") or info.get("hasOff")):
        return True, "promo input replaced by applied discount"
    return False, ""


def is_payment_pages_update(response) -> bool:
    try:
        if response.request.method != "POST":
            return False
        url = response.url
        if "api.stripe.com/v1/payment_pages/" not in url:
            return False
        if url.rstrip("/").endswith("/init"):
            return False
        return True
    except Exception:
        return False


def enter_code(page, code: str) -> None:
    open_promo_input(page)
    promo = page.locator(PROMO_INPUT).first
    promo.wait_for(state="visible", timeout=15000)
    promo.click()
    promo.fill("")
    page.wait_for_timeout(120)
    # Human-like typing — more reliable with Stripe's React input
    promo.press_sequentially(code, delay=50)
    page.wait_for_timeout(250)
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
    # Wait briefly for Apply to finish any exit animation from a prior remove.
    try:
        page.wait_for_function(
            """() => {
              const buttons = [...document.querySelectorAll('button')];
              return buttons.some(b => {
                const cls = b.className || '';
                const text = (b.innerText || '').trim();
                const isApply = cls.includes('PromotionCodeEntry-applyButton') || text === 'Apply';
                return isApply && !b.disabled && !cls.includes('applyButtonIsExiting') && b.offsetParent !== null;
              });
            }""",
            timeout=8000,
        )
    except PlaywrightTimeout:
        pass

    apply_btns = page.locator(APPLY_BTN)
    for i in range(apply_btns.count()):
        btn = apply_btns.nth(i)
        try:
            cls = btn.get_attribute("class") or ""
            if "applyButtonIsExiting" in cls:
                continue
            if btn.is_visible() and btn.is_enabled():
                btn.click(timeout=5000)
                return
        except Exception:
            continue
    page.locator(PROMO_INPUT).first.press("Enter")


def classify_stripe_response(response) -> tuple[str, str]:
    try:
        status = response.status
        body = response.text()
    except Exception as exc:
        return "unknown", f"response read error: {exc}"

    try:
        data = json.loads(body)
    except Exception:
        data = None

    if status == 200:
        if isinstance(data, dict) and data.get("error"):
            msg = data["error"].get("message") or str(data["error"])
            return "not_working", msg
        return "working", f"stripe payment_pages HTTP {status}"

    msg = ""
    if isinstance(data, dict):
        err = data.get("error") or {}
        msg = err.get("message") or err.get("code") or ""
    if not msg:
        msg = (body or "")[:200]
    if status >= 400:
        return "not_working", msg or f"stripe HTTP {status}"
    return "unknown", f"stripe HTTP {status}"


def apply_coupon(page, code: str) -> tuple[bool, str]:
    clear_existing_promo(page)
    open_promo_input(page)

    before_total = get_total_due_today(page)
    enter_code(page, code)

    api_result: tuple[str, str] | None = None
    try:
        with page.expect_response(is_payment_pages_update, timeout=20000) as resp_info:
            click_apply(page)
        api_result = classify_stripe_response(resp_info.value)
    except PlaywrightTimeout:
        page.wait_for_timeout(2000)
    except Exception:
        page.wait_for_timeout(2000)

    page.wait_for_timeout(900)

    if api_result is not None:
        status, detail = api_result
        if status == "working":
            ok, ui_detail = promo_is_applied(page, code)
            after = get_total_due_today(page)
            if ok:
                return True, ui_detail
            if before_total is not None and after is not None and after < before_total - 0.001:
                return True, f"total {before_total} -> {after}"
            return True, detail
        if status == "not_working":
            err = visible_promo_error(page)
            return False, err or detail or "rejected by Stripe"

    err = visible_promo_error(page)
    if err:
        return False, err

    ok, detail = promo_is_applied(page, code)
    if ok:
        return True, detail

    after_total = get_total_due_today(page)
    if before_total is not None and after_total is not None and after_total < before_total - 0.001:
        return True, f"total {before_total} -> {after_total}"
    if before_total is not None and after_total is not None and after_total == before_total:
        return False, "no discount / total unchanged"
    return False, "could not confirm application"


def run(url: str, coupons: list[str], headed: bool, slow_mo: int, output: Path | None) -> int:
    results: list[tuple[str, bool, str]] = []
    chrome = ChromeCDP(headed=headed)

    try:
        cdp_url = chrome.start()
    except Exception as exc:
        print(f"ERROR: could not launch Chrome: {exc}", file=sys.stderr)
        print(
            "Install Google Chrome and keep HEADED=True. "
            "Stripe blocks Playwright/headless browsers for promo codes.",
            file=sys.stderr,
        )
        return 2

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            # Prefer the default tab Chrome opened; new tabs are fine too.
            page = context.pages[0] if context.pages else context.new_page()

            print(f"Opening checkout: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                ua = page.evaluate("() => navigator.userAgent")
                print(f"Browser UA: {ua}")
                if "HeadlessChrome" in (ua or ""):
                    print(
                        "WARNING: HeadlessChrome detected — Stripe will likely "
                        "mark every promo invalid. Set HEADED=True.",
                        file=sys.stderr,
                    )
            except Exception:
                pass

            try:
                page.wait_for_selector(
                    f"{PROMO_INPUT}, {APPLIED}, "
                    '[data-testid="product-summary-promo-code"], '
                    '[data-testid="checkout-container"]',
                    timeout=45000,
                )
            except PlaywrightTimeout:
                print("ERROR: Checkout page did not load expected elements.", file=sys.stderr)
                return 2

            page.wait_for_timeout(2500)
            clear_existing_promo(page)
            open_promo_input(page)

            for idx, code in enumerate(coupons, start=1):
                print(f"[{idx}/{len(coupons)}] Trying: {code} ... ", end="", flush=True)
                try:
                    working, detail = apply_coupon(page, code)
                except Exception as exc:
                    working, detail = False, f"error: {exc}"
                print(("working" if working else "not working") + f" ({detail})")
                results.append((code, working, detail))
                page.wait_for_timeout(500)

            try:
                page.close()
            except Exception:
                pass
    finally:
        chrome.stop()

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
        lines = [
            f"{'working' if ok else 'not working'}\t{code}\t{detail}"
            for code, ok, detail in results
        ]
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWrote results to {output}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test Mobbin Stripe promo codes using real Chrome (CDP)."
    )
    parser.add_argument("--url", default=None, help="Stripe Checkout URL")
    parser.add_argument("--file", "-f", default=None, help="Coupons file")
    parser.add_argument("--output", "-o", default=None, help="TSV results path")
    parser.add_argument(
        "--headed",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show Chrome window (default True; required for Stripe)",
    )
    parser.add_argument("--slow-mo", type=int, default=None, help="Unused with CDP; kept for compat")
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
