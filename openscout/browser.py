from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from openscout.config import Settings
from openscout.models import Element, Snapshot

SNAPSHOT_JS = """
() => {
  const visible = (el) => {
    if (!el || !el.getBoundingClientRect) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
      return false;
    }
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    if (r.bottom < 0 || r.right < 0 || r.top > innerHeight || r.left > innerWidth) return false;
    return true;
  };
  const accName = (el) => {
    const aria = el.getAttribute("aria-label") || "";
    if (aria) return aria.trim();
    const id = el.getAttribute("id");
    if (id) {
      const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (lab) return lab.innerText.trim();
    }
    const wrap = el.closest("label");
    if (wrap) return wrap.innerText.trim();
    return (el.innerText || el.getAttribute("value") || el.getAttribute("alt") || el.getAttribute("title") || "").trim();
  };
  const selector = 'a, button, input, select, textarea, summary, [role="button"], [role="link"], [role="tab"]';
  const elements = [];
  for (const el of document.querySelectorAll(selector)) {
    if (!visible(el)) continue;
    const idx = elements.length;
    el.setAttribute("data-openscout-id", String(idx));
    const r = el.getBoundingClientRect();
    elements.push({
      id: idx,
      tag: el.tagName.toLowerCase(),
      type: (el.getAttribute("type") || "").toLowerCase(),
      role: el.getAttribute("role") || "",
      text: (el.innerText || "").trim().slice(0, 200),
      name: el.getAttribute("name") || "",
      href: el.getAttribute("href") || "",
      placeholder: el.getAttribute("placeholder") || "",
      aria: el.getAttribute("aria-label") || "",
      testid: el.getAttribute("data-testid") || "",
      label: accName(el).slice(0, 200),
      disabled: !!(el.disabled || el.getAttribute("aria-disabled") === "true"),
      x: r.x, y: r.y, w: r.width, h: r.height,
    });
  }
  const images = [...document.querySelectorAll("img")].map((img) => ({
    src: img.getAttribute("src") || "",
    alt: img.getAttribute("alt"),
    hasAlt: img.hasAttribute("alt"),
    visible: visible(img),
  }));
  return {
    url: location.href,
    title: document.title,
    text: (document.body && document.body.innerText || "").slice(0, 12000),
    elements,
    images,
  };
}
"""


class BrowserSession:
    def __init__(self, settings: Settings, run_dir: Path) -> None:
        self.settings = settings
        self.run_dir = run_dir
        self.screenshots = run_dir / "screenshots"
        self.screenshots.mkdir(parents=True, exist_ok=True)
        self._pw = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.console: list[dict[str, Any]] = []
        self.page_errors: list[str] = []
        self.network: list[dict[str, Any]] = []
        self.pages_visited: list[str] = []

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=self.settings.headless,
            slow_mo=self.settings.slow_mo,
        )
        self.context = await self.browser.new_context(viewport={"width": 1280, "height": 800})
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.settings.timeout_ms)
        self.page.on("console", self._on_console)
        self.page.on("pageerror", self._on_page_error)
        self.page.on("response", self._on_response)

    def _on_console(self, message: Any) -> None:
        try:
            self.console.append(
                {
                    "type": message.type,
                    "text": message.text,
                    "url": self.page.url if self.page else "",
                }
            )
        except Exception:
            return

    def _on_page_error(self, error: Any) -> None:
        self.page_errors.append(str(error))

    def _on_response(self, response: Any) -> None:
        try:
            status = response.status
            url = response.url
            if status >= 400:
                self.network.append({"status": status, "url": url, "page": self.page.url if self.page else ""})
        except Exception:
            return

    async def goto(self, url: str) -> None:
        assert self.page
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(200)
        self._remember()

    def _remember(self) -> None:
        if self.page and self.page.url not in self.pages_visited:
            self.pages_visited.append(self.page.url)

    async def snapshot(self) -> Snapshot:
        assert self.page
        raw = await self.page.evaluate(SNAPSHOT_JS)
        self._remember()
        return Snapshot(
            url=raw["url"],
            title=raw["title"],
            text=raw["text"],
            elements=[Element(**item) for item in raw["elements"]],
            images=raw.get("images") or [],
        )

    async def click(self, element_id: int) -> None:
        assert self.page
        locator = self.page.locator(f'[data-openscout-id="{element_id}"]')
        await locator.click(timeout=self.settings.timeout_ms)
        await self.page.wait_for_timeout(250)
        self._remember()

    async def fill(self, element_id: int, value: str) -> None:
        assert self.page
        locator = self.page.locator(f'[data-openscout-id="{element_id}"]')
        await locator.fill(value, timeout=self.settings.timeout_ms)

    async def select(self, element_id: int, value: str) -> None:
        assert self.page
        locator = self.page.locator(f'[data-openscout-id="{element_id}"]')
        await locator.select_option(value)

    async def check(self, element_id: int, checked: bool) -> None:
        assert self.page
        locator = self.page.locator(f'[data-openscout-id="{element_id}"]')
        await locator.set_checked(checked)

    async def screenshot(self, name: str) -> str:
        assert self.page
        path = self.screenshots / name
        await self.page.screenshot(path=str(path), full_page=True)
        return str(path.relative_to(self.run_dir))

    async def wait_ms(self, ms: int) -> None:
        assert self.page
        await self.page.wait_for_timeout(ms)

    def consume_new_console_errors(self, seen: int) -> list[dict[str, Any]]:
        fresh = self.console[seen:]
        return [item for item in fresh if item.get("type") in {"error", "assert"}]

    def consume_new_page_errors(self, seen: int) -> list[str]:
        return self.page_errors[seen:]

    def consume_new_network(self, seen: int) -> list[dict[str, Any]]:
        return self.network[seen:]

    async def close(self) -> None:
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()

    def dump_signals(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {"console": self.console, "page_errors": self.page_errors, "network": self.network},
                indent=2,
            ),
            encoding="utf-8",
        )
