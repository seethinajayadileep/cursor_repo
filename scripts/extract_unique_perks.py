#!/usr/bin/env python3
"""Fetch partner perk URLs and extract unique vendor offers with local context."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests

CSV_PATH = Path("/home/ubuntu/.cursor/projects/workspace/uploads/partner-perk-pages-MASTER_e0ca.csv")
OUT_DIR = Path("/workspace/output/partner-perks")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
TIMEOUT = 12
WORKERS = 24
MAX_TEXT = 24000

# Ambiguous tokens omitted: intel, lever, front, close, clay, wise, square,
# bench, drift, heap, render, neon, linear, make, check, crisp, ram, apollo, segment, fire.
VENDOR_ALIASES = {
    "amazon web services": "AWS",
    "aws activate": "AWS",
    "aws credits": "AWS",
    "google cloud platform": "Google Cloud",
    "google cloud": "Google Cloud",
    "google for startups": "Google Cloud",
    "google workspace": "Google Workspace",
    "microsoft azure": "Microsoft Azure",
    "azure credits": "Microsoft Azure",
    "microsoft 365": "Microsoft 365",
    "openai": "OpenAI",
    "chatgpt": "OpenAI",
    "anthropic": "Anthropic",
    "elevenlabs": "ElevenLabs",
    "eleven labs": "ElevenLabs",
    "hubspot for startups": "HubSpot",
    "hubspot": "HubSpot",
    "notion for startups": "Notion",
    "notion": "Notion",
    "stripe atlas": "Stripe Atlas",
    "stripe": "Stripe",
    "twilio": "Twilio",
    "sendgrid": "SendGrid",
    "slack": "Slack",
    "intercom": "Intercom",
    "zendesk": "Zendesk",
    "deel": "Deel",
    "rippling": "Rippling",
    "gusto": "Gusto",
    "carta": "Carta",
    "mercury": "Mercury",
    "brex": "Brex",
    "ramp": "Ramp",
    "airwallex": "Airwallex",
    "digitalocean": "DigitalOcean",
    "github copilot": "GitHub Copilot",
    "github": "GitHub",
    "vercel": "Vercel",
    "cloudflare": "Cloudflare",
    "datadog": "Datadog",
    "mongodb": "MongoDB",
    "mixpanel": "Mixpanel",
    "amplitude": "Amplitude",
    "figma": "Figma",
    "loom": "Loom",
    "calendly": "Calendly",
    "typeform": "Typeform",
    "airtable": "Airtable",
    "1password": "1Password",
    "okta": "Okta",
    "auth0": "Auth0",
    "mailchimp": "Mailchimp",
    "salesforce": "Salesforce",
    "snowflake": "Snowflake",
    "databricks": "Databricks",
    "hugging face": "Hugging Face",
    "huggingface": "Hugging Face",
    "replicate": "Replicate",
    "perplexity": "Perplexity",
    "midjourney": "Midjourney",
    "canva": "Canva",
    "webflow": "Webflow",
    "framer": "Framer",
    "shopify": "Shopify",
    "klaviyo": "Klaviyo",
    "customer.io": "Customer.io",
    "posthog": "PostHog",
    "sentry": "Sentry",
    "pagerduty": "PagerDuty",
    "heroku": "Heroku",
    "netlify": "Netlify",
    "supabase": "Supabase",
    "firebase": "Firebase",
    "docusign": "DocuSign",
    "firstbase": "Firstbase",
    "angellist": "AngelList",
    "wellfound": "Wellfound",
    "linkedin recruiter": "LinkedIn Recruiter",
    "greenhouse": "Greenhouse",
    "ashby": "Ashby",
    "workable": "Workable",
    "grammarly": "Grammarly",
    "superhuman": "Superhuman",
    "pipedrive": "Pipedrive",
    "freshworks": "Freshworks",
    "freshdesk": "Freshdesk",
    "atlassian": "Atlassian",
    "confluence": "Atlassian",
    "asana": "Asana",
    "monday.com": "monday.com",
    "clickup": "ClickUp",
    "miro": "Miro",
    "lucidchart": "Lucid",
    "nvidia inception": "NVIDIA",
    "nvidia": "NVIDIA",
    "coreweave": "CoreWeave",
    "together ai": "Together AI",
    "mistral": "Mistral AI",
    "cohere": "Cohere",
    "stability ai": "Stability AI",
    "runway": "Runway",
    "descript": "Descript",
    "riverside": "Riverside",
    "otter.ai": "Otter.ai",
    "zapier": "Zapier",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "qdrant": "Qdrant",
    "elasticsearch": "Elastic",
    "planetscale": "PlanetScale",
    "railway": "Railway",
    "fly.io": "Fly.io",
    "cloudinary": "Cloudinary",
    "contentful": "Contentful",
    "algolia": "Algolia",
    "hotjar": "Hotjar",
    "fullstory": "FullStory",
    "braze": "Braze",
    "iterable": "Iterable",
    "mailgun": "Mailgun",
    "postmark": "Postmark",
    "resend": "Resend",
    "plaid": "Plaid",
    "payoneer": "Payoneer",
    "quickbooks": "QuickBooks",
    "xero": "Xero",
    "netsuite": "NetSuite",
    "expensify": "Expensify",
    "navan": "Navan",
    "lattice": "Lattice",
    "culture amp": "Culture Amp",
    "bamboohr": "BambooHR",
    "personio": "Personio",
    "hibob": "HiBob",
    "justworks": "Justworks",
    "checkr": "Checkr",
    "docsend": "DocSend",
    "pitchbook": "PitchBook",
    "crunchbase": "Crunchbase",
    "affinity": "Affinity",
    "attio": "Attio",
    "salesloft": "Salesloft",
    "zoominfo": "ZoomInfo",
    "instantly": "Instantly",
    "lemlist": "Lemlist",
    "clearbit": "Clearbit",
    "mutiny": "Mutiny",
    "unbounce": "Unbounce",
    "squarespace": "Squarespace",
    "namecheap": "Namecheap",
    "backblaze": "Backblaze",
    "fastly": "Fastly",
    "new relic": "New Relic",
    "grafana": "Grafana",
    "betterstack": "Better Stack",
    "logrocket": "LogRocket",
    "bugsnag": "Bugsnag",
    "rollbar": "Rollbar",
    "circleci": "CircleCI",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    "hashicorp": "HashiCorp",
    "google gemini": "Google Gemini",
    "vertex ai": "Google Cloud",
    "vouch insurance": "Vouch",
    "vouch": "Vouch",
    "rho.co": "Rho",
    " rho ": "Rho",
    "pleo": "Pleo",
    "remofirst": "RemoFirst",
    "razorpay": "Razorpay",
    "ovhcloud": "OVHcloud",
    "wework": "WeWork",
    "alchemy": "Alchemy",
    "ravio": "Ravio",
    "cursor": "Cursor",
    "copilot": "GitHub Copilot",
    "pilot.com": "Pilot",
    "gcp": "Google Cloud",
    " aws ": "AWS",
    "ovh": "OVHcloud",
}

# Tokens that must be whole words
WORD_ALIASES = {k: v for k, v in VENDOR_ALIASES.items() if k.strip() == k}
ALIAS_KEYS = sorted(WORD_ALIASES.keys(), key=len, reverse=True)

OFFER_RE = re.compile(
    r"(?:"
    r"up to\s+(?:US\$|USD\s*|€|£|\$)\s?[\d,.]+[kKmMbB]?(?:\s*(?:in)?\s*(?:credits?|discounts?|in credits?))?"
    r"|(?:US\$|USD\s*|€|£|\$)\s?[\d,.]+[kKmMbB]?\+?\s*(?:in\s+)?(?:free\s+)?(?:credits?|cloud credits?)"
    r"|\b\d{1,3}%\s+off(?:\s+(?:for\s+)?(?:the\s+)?(?:first|1st)\s+(?:year|month))?"
    r"|\b(?:free|waived)\s+(?:for\s+)?(?:the\s+)?(?:first\s+)?\d+\s*(?:days?|months?|years?)"
    r"|\b\d+[-\s]day\s+(?:free\s+)?trial"
    r"|fee waivers?"
    r"|\b0%\s+equity"
    r"|\b\d+\s+free\s+(?:benchmarks?|seats?|months?|licenses?)"
    r"|credits?\s+(?:worth\s+)?(?:up to\s+)?(?:US\$|USD\s*|€|£|\$)\s?[\d,.]+[kKmMbB]?"
    r")"
    ,
    re.I,
)

HOST_VENDOR = {
    "deel.com": "Deel",
    "github.com": "GitHub",
    "vouch.us": "Vouch",
    "rho.co": "Rho",
    "remofirst.com": "RemoFirst",
    "digitalocean.com": "DigitalOcean",
    "ramp.com": "Ramp",
    "pleo.io": "Pleo",
    "razorpay.com": "Razorpay",
    "brex.com": "Brex",
    "rippling.com": "Rippling",
    "hubspot.com": "HubSpot",
    "aws.amazon.com": "AWS",
    "airwallex.com": "Airwallex",
    "ravio.com": "Ravio",
}

CHROME_URLS: list[str] = []


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "h1", "h2", "h3", "h4", "li", "br", "div", "tr", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self.title += text + " "
        self.parts.append(text + " ")


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def html_to_text(html: str) -> tuple[str, str]:
    parser = TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    title = normalize_space(parser.title)
    text = normalize_space("".join(parser.parts))
    if not text:
        text = normalize_space(re.sub(r"<[^>]+>", " ", html))
    return title, text


def fetch_url(url: str) -> dict:
    result = {
        "url": url,
        "ok": False,
        "status": None,
        "final_url": url,
        "title": "",
        "text": "",
        "error": "",
        "elapsed_ms": 0,
    }
    t0 = time.time()
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        result["status"] = resp.status_code
        result["final_url"] = str(resp.url)
        if resp.status_code >= 400:
            result["error"] = f"http_{resp.status_code}"
            result["elapsed_ms"] = int((time.time() - t0) * 1000)
            return result
        html = resp.content[:500_000].decode(resp.encoding or "utf-8", errors="ignore")
        title, text = html_to_text(html)
        result["title"] = title[:300]
        result["text"] = text[:MAX_TEXT]
        result["ok"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
    result["elapsed_ms"] = int((time.time() - t0) * 1000)
    return result


def chrome_dump(url: str) -> dict:
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--virtual-time-budget=12000",
        "--dump-dom",
        url,
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=40)
        html = proc.stdout.decode("utf-8", errors="ignore")[:700_000]
        title, text = html_to_text(html)
        return {
            "url": url,
            "ok": bool(text) and proc.returncode == 0,
            "status": 200 if proc.returncode == 0 else proc.returncode,
            "final_url": url,
            "title": title[:300],
            "text": text[:MAX_TEXT],
            "error": "" if proc.returncode == 0 else proc.stderr.decode("utf-8", errors="ignore")[:300],
            "elapsed_ms": int((time.time() - t0) * 1000),
            "via": "chrome",
        }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "status": None,
            "final_url": url,
            "title": "",
            "text": "",
            "error": str(exc)[:300],
            "elapsed_ms": int((time.time() - t0) * 1000),
            "via": "chrome",
        }


def vendor_spans(text: str) -> list[tuple[str, int, int]]:
    lower = f" {text.lower()} "
    found: list[tuple[str, int, int]] = []
    seen_at: set[tuple[str, int]] = set()
    for key in ALIAS_KEYS:
        if key.startswith(" ") or key.endswith(" "):
            needle = key
            start_idx = 0
            hay = f" {text.lower()} "
            while True:
                i = hay.find(needle, start_idx)
                if i < 0:
                    break
                # map back (hay has leading space)
                real = i - 1
                name = WORD_ALIASES[key]
                if (name, real) not in seen_at:
                    seen_at.add((name, real))
                    found.append((name, max(0, real), real + len(needle)))
                start_idx = i + len(needle)
            continue
        pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(key)}(?![A-Za-z0-9])", re.I)
        for m in pat.finditer(text):
            name = WORD_ALIASES[key]
            if (name, m.start()) not in seen_at:
                seen_at.add((name, m.start()))
                found.append((name, m.start(), m.end()))
    return found


def offers_near(text: str, start: int, end: int, window: int = 220) -> list[str]:
    lo = max(0, start - window)
    hi = min(len(text), end + window)
    blob = text[lo:hi]
    hits = []
    for m in OFFER_RE.finditer(blob):
        val = normalize_space(m.group(0))
        if val and val.lower() not in {h.lower() for h in hits}:
            hits.append(val)
    return hits[:6]


def snippet(text: str, start: int, end: int, window: int = 160) -> str:
    lo = max(0, start - window)
    hi = min(len(text), end + window)
    return normalize_space(text[lo:hi])[:420]


def load_rows() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def add_source(store, vendor, partner, url, offers, detail, conf, origin):
    rec = store.setdefault(
        vendor,
        {
            "vendor": vendor,
            "offers": [],
            "details": [],
            "partners": set(),
            "urls": set(),
            "confidence": set(),
            "origins": set(),
        },
    )
    rec["partners"].add(partner)
    if url:
        rec["urls"].add(url)
    if conf:
        rec["confidence"].add(conf.lower())
    rec["origins"].add(origin)
    for offer in offers:
        offer = normalize_space(offer)
        if offer and offer not in rec["offers"] and len(rec["offers"]) < 12:
            rec["offers"].append(offer)
    detail = normalize_space(detail)
    if detail and detail not in rec["details"] and len(rec["details"]) < 6:
        rec["details"].append(detail[:480])


SKIP_NOTE = re.compile(r"no public (deal|perk)|not found|not a (classic )?(discount|vendor)|VERIFY_REMOVED", re.I)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    url_to_partners: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        url = (r.get("PerkURL") or "").strip()
        url_to_partners[url].append(r)

    unique_urls = [u for u in url_to_partners if u]
    print(f"rows={len(rows)} unique_urls={len(unique_urls)}", flush=True)

    fetches: dict[str, dict] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_url, u): u for u in unique_urls}
        for fut in as_completed(futs):
            url = futs[fut]
            try:
                fetches[url] = fut.result()
            except Exception as exc:
                fetches[url] = {
                    "url": url,
                    "ok": False,
                    "status": None,
                    "final_url": url,
                    "title": "",
                    "text": "",
                    "error": str(exc)[:300],
                    "elapsed_ms": 0,
                }
            done += 1
            if done % 100 == 0 or done == len(unique_urls):
                ok = sum(1 for v in fetches.values() if v.get("ok"))
                print(f"fetched {done}/{len(unique_urls)} ok={ok}", flush=True)

    print("chrome dumps...", flush=True)
    for url in CHROME_URLS:
        dumped = chrome_dump(url)
        prev = fetches.get(url) or {}
        if len(dumped.get("text") or "") > len(prev.get("text") or ""):
            fetches[url] = dumped
            print(f"  chrome {url} chars={len(dumped.get('text') or '')}", flush=True)
        else:
            print(f"  chrome skip/keep http {url} chrome_chars={len(dumped.get('text') or '')}", flush=True)

    fetch_path = OUT_DIR / "fetch_results.jsonl"
    with fetch_path.open("w", encoding="utf-8") as f:
        for url in unique_urls:
            rec = {k: v for k, v in fetches[url].items() if k != "text"}
            rec["text_len"] = len(fetches[url].get("text") or "")
            rec["snippet"] = (fetches[url].get("text") or "")[:700]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    store: dict[str, dict] = {}

    for url, partners in url_to_partners.items():
        page = fetches.get(url) or {}
        page_text = page.get("text") or ""
        page_title = page.get("title") or ""
        host = host_of(url)
        host_vendor = HOST_VENDOR.get(host)

        for r in partners:
            partner = r.get("Partner") or ""
            notes = r.get("Notes") or ""
            conf = r.get("Confidence") or ""
            note_text = notes
            combined_page = f"{page_title}\n{page_text}"

            # CSV notes: only vendors actually named in the note, with nearby terms.
            for name, s, e in vendor_spans(note_text):
                offs = offers_near(note_text, s, e, window=160)
                add_source(store, name, partner, url, offs, snippet(note_text, s, e) or notes, conf, "csv_notes")

            if host_vendor:
                # Partner landing pages (deel.com/partners/X, vouch.us/venture/X, …)
                # describe that vendor's perk — do not scrape footer/nav brands.
                host_blob = f"{notes}\n{page_title}\n{combined_page[:4000]}"
                offs = []
                for name, s, e in vendor_spans(host_blob):
                    if name == host_vendor:
                        offs.extend(offers_near(host_blob, s, e, window=180))
                if not offs:
                    offs = [m.group(0) for m in OFFER_RE.finditer(notes)][:4]
                add_source(
                    store,
                    host_vendor,
                    partner,
                    url,
                    offs,
                    (notes or page_title or combined_page[:240]),
                    conf,
                    "vendor_partner_page",
                )
            else:
                for name, s, e in vendor_spans(combined_page):
                    offs = offers_near(combined_page, s, e, window=140)
                    add_source(
                        store,
                        name,
                        partner,
                        url,
                        offs,
                        snippet(combined_page, s, e),
                        conf,
                        "live_page",
                    )

            if not vendor_spans(note_text) and not vendor_spans(combined_page) and not host_vendor:
                if notes and not SKIP_NOTE.search(notes):
                    # keep as a non-vendor program perk only if it mentions credits/discounts/perks
                    if re.search(r"perk|credit|discount|off\b|marketplace|deal", notes, re.I):
                        add_source(
                            store,
                            f"Program support: {partner}",
                            partner,
                            url,
                            [m.group(0) for m in OFFER_RE.finditer(notes)][:3],
                            notes,
                            conf,
                            "program_notes",
                        )

    unique_rows = []
    for vendor, rec in sorted(
        store.items(), key=lambda kv: (-len(kv[1]["partners"]), kv[0].lower())
    ):
        unique_rows.append(
            {
                "vendor_or_perk": vendor,
                "offer_details": " | ".join(rec["offers"]) if rec["offers"] else "See supporting details (terms vary by partner)",
                "supporting_details": " || ".join(rec["details"][:4]),
                "partner_count": len(rec["partners"]),
                "example_partners": "; ".join(sorted(rec["partners"])[:15]),
                "example_urls": "; ".join(sorted(rec["urls"])[:8]),
                "sources": "; ".join(sorted(rec["origins"])),
                "confidence_mix": "; ".join(sorted(rec["confidence"])),
            }
        )

    csv_path = OUT_DIR / "unique_perks.csv"
    fields = [
        "vendor_or_perk",
        "offer_details",
        "supporting_details",
        "partner_count",
        "example_partners",
        "example_urls",
        "sources",
        "confidence_mix",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(unique_rows)

    ok = sum(1 for v in fetches.values() if v.get("ok"))
    stats = {
        "source_rows": len(rows),
        "unique_urls": len(unique_urls),
        "fetch_ok": ok,
        "fetch_fail": len(unique_urls) - ok,
        "unique_vendors_or_programs": len(unique_rows),
        "vendor_rows": sum(1 for r in unique_rows if not r["vendor_or_perk"].startswith("Program support:")),
        "program_rows": sum(1 for r in unique_rows if r["vendor_or_perk"].startswith("Program support:")),
    }
    (OUT_DIR / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2), flush=True)
    print("top vendors:")
    for r in unique_rows[:30]:
        print(f"  {r['partner_count']:4} {r['vendor_or_perk']}: {r['offer_details'][:100]}")


if __name__ == "__main__":
    main()
