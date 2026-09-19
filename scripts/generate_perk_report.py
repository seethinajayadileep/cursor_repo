#!/usr/bin/env python3
"""Turn extracted vendor rows into a readable unique-perks catalog."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

SRC = Path("/workspace/output/partner-perks/unique_perks.csv")
STATS = Path("/workspace/output/partner-perks/stats.json")
OUT_MD = Path("/workspace/output/partner-perks/UNIQUE_PERKS.md")
OUT_CSV = Path("/workspace/output/partner-perks/unique_perks_clean.csv")

JUNK = re.compile(
    r"\$10M\+|€4M|up to \$7M|up to \$4\b|up to \$1\b|\$650k cloud credits|up to \$430\b",
    re.I,
)

CATEGORIES = {
    "Cloud & infrastructure": [
        "AWS",
        "Google Cloud",
        "Microsoft Azure",
        "DigitalOcean",
        "Vercel",
        "Cloudflare",
        "Heroku",
        "Railway",
        "Render",
        "Fly.io",
        "Supabase",
        "Firebase",
        "OVHcloud",
        "Alchemy",
        "CoreWeave",
    ],
    "AI models & AI tools": [
        "OpenAI",
        "Anthropic",
        "ElevenLabs",
        "NVIDIA",
        "Mistral AI",
        "Cohere",
        "Hugging Face",
        "Replicate",
        "Perplexity",
        "Google Gemini",
        "Cursor",
        "Runway",
        "Midjourney",
        "Together AI",
        "Pinecone",
        "Weaviate",
        "Qdrant",
    ],
    "CRM, marketing & support": [
        "HubSpot",
        "Salesforce",
        "Pipedrive",
        "Intercom",
        "Zendesk",
        "Freshworks",
        "Customer.io",
        "Klaviyo",
        "Mailchimp",
        "Braze",
        "Instantly",
        "Lemlist",
        "Crunchbase",
        "Apollo.io",
        "Attio",
        "Clearbit",
        "Mutiny",
        "Unbounce",
        "Hotjar",
        "FullStory",
        "DocSend",
    ],
    "Payments, banking & spend": [
        "Stripe",
        "Stripe Atlas",
        "Brex",
        "Ramp",
        "Mercury",
        "Rho",
        "Airwallex",
        "Pleo",
        "Razorpay",
        "Plaid",
        "Payoneer",
        "Navan",
        "Expensify",
    ],
    "HR, payroll, EOR & talent": [
        "Deel",
        "Rippling",
        "RemoFirst",
        "Gusto",
        "Justworks",
        "Personio",
        "HiBob",
        "Lattice",
        "Greenhouse",
        "Ashby",
        "AngelList",
        "Wellfound",
    ],
    "Insurance, legal & cap table": [
        "Vouch",
        "Carta",
        "DocuSign",
        "Ravio",
        "Pilot",
        "Firstbase",
    ],
    "Dev tools, data & observability": [
        "GitHub",
        "GitHub Copilot",
        "GitLab",
        "MongoDB",
        "Datadog",
        "Sentry",
        "PostHog",
        "Mixpanel",
        "Amplitude",
        "Twilio",
        "SendGrid",
        "Resend",
        "Mailgun",
        "Postmark",
        "Algolia",
        "Snowflake",
        "Databricks",
        "Grafana",
        "CircleCI",
        "Auth0",
        "Okta",
        "New Relic",
        "Bitbucket",
        "Cloudinary",
    ],
    "Productivity, collab & design": [
        "Notion",
        "Slack",
        "Miro",
        "Figma",
        "Airtable",
        "Webflow",
        "Framer",
        "Canva",
        "Typeform",
        "Loom",
        "Asana",
        "Atlassian",
        "ClickUp",
        "monday.com",
        "Calendly",
        "Superhuman",
        "Grammarly",
        "1Password",
        "Zapier",
        "WeWork",
        "Google Workspace",
        "Microsoft 365",
        "Shopify",
        "Squarespace",
        "Namecheap",
        "Xero",
        "QuickBooks",
        "NetSuite",
        "PitchBook",
        "Affinity",
        "ZoomInfo",
        "Contentful",
        "Riverside",
        "Backblaze",
        "Fastly",
    ],
}

CANONICAL = {
    "AWS": "AWS Activate / portfolio credits: commonly up to $5K–$100K, and up to ~$200K on stronger Activate or VC-portfolio packages. Cloud credits, not cash.",
    "Google Cloud": "Google for Startups Cloud Program: often $2K–$100K+ in GCP credits; some accelerator/VC paths advertise up to ~$200K. Eligibility usually requires an official partner referral.",
    "Microsoft Azure": "Microsoft for Startups / Azure credits: commonly $1K–$25K for early startups, with some funds advertising up to ~$100K–$250K Azure credits for portfolio companies.",
    "DigitalOcean": "DigitalOcean for Startups: typically $1K–$2.5K in credit on public partner pages; some programs list up to $100K for qualified startups.",
    "Vercel": "Vercel for Startups: partner catalogs commonly list about $5K–$30K in credits depending on the program tier.",
    "Cloudflare": "Cloudflare for Startups: credits/plan upgrades via partner catalogs (amount varies; often bundled in VC marketplace totals).",
    "OVHcloud": "OVHcloud startup credits appear in European partner catalogs (e.g. Angel Invest); amounts vary by program.",
    "OpenAI": "OpenAI API / ChatGPT credits via accelerators and VC marketplaces. Public partner pages range from a few thousand dollars up to much larger API credits on select programs; terms are invite/eligibility gated.",
    "Anthropic": "Anthropic/Claude API credits via partner stacks. Typical listed amounts are in the low thousands of dollars in credits; larger packages exist on select AI-focused programs.",
    "ElevenLabs": "ElevenLabs for Startups / partner packs: commonly 40–70% off or character/credit grants (examples include ~$500–$12K credits or 12 months / tens of millions of characters on builder packages).",
    "NVIDIA": "NVIDIA Inception: platform benefits, pricing, and sometimes cloud/GPU credits. Partner pages advertise anywhere from tens of thousands up to ~$150K–$350K in related credits depending on the program.",
    "HubSpot": "HubSpot for Startups: most commonly up to 90% off year one for eligible early startups (often <~$2M raised or accelerator/alumni status); larger companies may see ~50% off. Some pages also mention HubSpot credits.",
    "Salesforce": "Salesforce for Startups: trial plus substantial first-year discounts (partner pages cite ~50–90% off subject to eligibility).",
    "Intercom": "Intercom / Fin startup packs: free or heavily discounted first year (examples include free for 1 year, 25–100% off, or bundled $500K+ partner-deal access on some pages).",
    "Zendesk": "Zendesk for Startups: typically first-month or first-year discounts (examples: 10% off first month, up to ~75–90% off year one) plus occasional credits.",
    "Stripe": "Stripe for Startups / Atlas: fee waivers or credits (examples: ~$20K Atlas-style credits, 90% off Atlas on some packs) plus payment processing — not cloud GPU credits.",
    "Stripe Atlas": "Stripe Atlas company-formation discount/credits for eligible startups via partner programs.",
    "Brex": "Brex for Startups: founder banking/card perks — credits, fee-free accounts, and sometimes 30–50% off first-year services. Amounts like $5K credits appear on several partner pages.",
    "Ramp": "Ramp for Startups: corporate cards, 1.5%+ cashback style rewards, and partner credits (public pages mention ~$1.5K–$5K+ credits or larger ‘up to $250K’ marketplace-style packages on some VC pages).",
    "Mercury": "Mercury banking perks for venture-backed startups (priority onboarding, credits, sometimes partner software credits).",
    "Rho": "Rho treasury/banking for portfolio companies: metal cards, statement credits (examples: $1.6K–$4K credits, Pods, travel/hardware gifts). Not a SaaS discount catalog.",
    "Airwallex": "Airwallex for Startups: fee waivers on FX/payments plus bundled partner credits.",
    "Pleo": "Pleo spend cards: partner pages advertise up to ~33% off or ~1% cashback for eligible VC portfolios.",
    "Deel": "Deel for Startups: free seats and EOR/payroll discounts for companies referred by a VC/accelerator partner. Public pages mention free seats, ~10 free EOR, credits around $5K–$6K, or large % off — terms are partner-specific.",
    "Rippling": "Rippling HR/IT/finance stack discounts via partner programs (often first-year % off; some pages bundle 50+ software deals).",
    "RemoFirst": "RemoFirst EOR: commonly 30–50% off plus 1–2 months free for partner-backed startups; some pages mention a first-month fee waiver.",
    "Gusto": "Gusto payroll discounts for startups via VC/accelerator partner pages.",
    "Vouch": "Vouch Insurance: venture-ready startup insurance (D&O, E&O, cyber, etc.) for named VC portfolios. This is an insurance product path, not AWS-style credits.",
    "Carta": "Carta cap-table / equity management: commonly ~10–25% off the first year (some pages 20% off first year) for partner-backed companies.",
    "GitHub": "GitHub for Startups: typically up to ~$10K in GitHub Enterprise/Actions credits via official ecosystem partners (many CSV rows are GitHub partner listing pages, not independent dealbooks).",
    "GitHub Copilot": "GitHub Copilot discounts or free months (examples: 80% off, free for 6 months) when bundled in GitHub for Startups or accelerator stacks.",
    "Notion": "Notion for Startups: plus/enterprise credits and % off. Public partner mentions include ~$1K–$12K credits, 6 months free, or 10–50% off depending on program.",
    "Slack": "Slack for Startups: typically ~50% off the first year (some catalogs 20–79% off or credits) for eligible early-stage companies.",
    "MongoDB": "MongoDB for Startups: credits commonly advertised around $5K–$50K plus a trial; some AI stacks list additional credits.",
    "Datadog": "Datadog for Startups: monitoring credits often listed around $50K–$100K, with some programs up to ~$250K–$500K.",
    "Sentry": "Sentry for Startups: plan credits / first-year discounts via partner catalogs.",
    "PostHog": "PostHog for Startups: product-analytics credits commonly $500–$50K depending on partner tier.",
    "Twilio": "Twilio / Segment startup credits (Segment pages mention up to ~$50K) plus communications credits in accelerator stacks.",
    "Webflow": "Webflow for Startups: 12 months free or credits often listed around $9K–$12K, with some catalogs up to $100K.",
    "Figma": "Figma for Startups: complimentary seats / first-year discounts via official startup and VC programs.",
    "Miro": "Miro for Startups: credits or 30–50%+ off (partner pages also mention $1K–$10K credits).",
    "Canva": "Canva for Startups / nonprofit-style discounts via some partner catalogs.",
    "WeWork": "WeWork for Startups: membership credits or discounts (often inside European VC marketplaces).",
    "Ravio": "Ravio compensation benchmarks: example partner offer is a 60-day free trial (for 100+ employees) or 15% off the first year, plus free benchmarks.",
    "Cursor": "Cursor IDE/pro credits or discounts appear in several AI/accelerator perk lists (amounts rarely standardized publicly).",
    "Shopify": "Shopify for Startups: extended trial and/or first-year discounts in partner catalogs.",
    "Auth0": "Auth0 for Startups: free tier expansion / credits via partner programs.",
    "Okta": "Okta for Startups: identity-platform discounts (pages mention ~10% off or credits in the low thousands).",
    "Pilot": "Pilot bookkeeping: startup credits (examples $1K–$10K) or ~25% off via partner programs.",
    "Resend": "Resend email API: partner catalogs list credits in the hundreds to low thousands of dollars.",
    "Typeform": "Typeform for Startups: first-year % off via partner catalogs.",
    "Airtable": "Airtable for Startups: credits (examples ~$1K) and large % off on some marketplace pages.",
    "Mixpanel": "Mixpanel for Startups: first-year discounts or credits via VC/accelerator partners.",
    "Amplitude": "Amplitude for Startups: credits/discounts in partner stacks.",
    "Pipedrive": "Pipedrive for Startups: substantial first-year % off on several partner pages.",
    "Freshworks": "Freshworks for Startups: CRM/support suite discounts via partner programs.",
    "Runway": "Runway ML: credits or ~20–50% off; some catalogs list up to a few thousand dollars or larger European credit packs.",
    "Replicate": "Replicate inference credits in AI perk aggregators and accelerator stacks.",
    "Hugging Face": "Hugging Face Pro/hardware or inference credits via AI startup programs.",
    "Perplexity": "Perplexity enterprise/API credits in some AI perk lists.",
    "Mistral AI": "Mistral API credits via AI-focused partner stacks.",
    "Cohere": "Cohere API credits via partner/AI programs.",
    "Algolia": "Algolia for Startups: search credits via partner catalogs.",
    "Snowflake": "Snowflake startup credits (data-cloud) via partner/VC programs.",
    "Databricks": "Databricks for Startups: platform credits in data/AI partner stacks.",
    "Cloudflare": "Cloudflare for Startups credits and plan upgrades.",
    "Firebase": "Firebase / Google credits often bundled with Google for Startups rather than a separate catalog.",
    "Supabase": "Supabase for Startups: database credits in modern app stacks.",
    "Heroku": "Heroku credits via older accelerator/cloud bundles.",
    "Railway": "Railway hosting credits in newer builder stacks.",
    "Fly.io": "Fly.io credits in some partner perk lists.",
    "Calendly": "Calendly for Startups: first-year discounts.",
    "Loom": "Loom for Startups: credits or % off via partner catalogs.",
    "Asana": "Asana for Startups: first-year discounts.",
    "Atlassian": "Atlassian Cloud for Startups: typically 1 year free of Standard cloud products then a discount year, subject to eligibility.",
    "ClickUp": "ClickUp for Startups: first-year discounts.",
    "monday.com": "monday.com for Startups: first-year discounts.",
    "1Password": "1Password for Startups: team-plan discounts / credits.",
    "Zapier": "Zapier for Startups: task credits or plan discounts.",
    "Grammarly": "Grammarly Business discounts in some partner catalogs.",
    "Superhuman": "Superhuman founder discounts in selected VC stacks.",
    "Google Workspace": "Google Workspace for Startups: often 12 months free / discounted seats via Google for Startups partners.",
    "Microsoft 365": "Microsoft 365 seats sometimes bundled with Microsoft for Startups.",
    "Xero": "Xero accounting discounts for startups via partner pages.",
    "QuickBooks": "QuickBooks for Startups: first-year % off.",
    "Lattice": "Lattice HR/performance discounts via partner programs.",
    "Greenhouse": "Greenhouse ATS discounts for venture-backed hiring teams.",
    "Ashby": "Ashby ATS startup pricing via partner introductions.",
    "Justworks": "Justworks PEO discounts on selected partner pages.",
    "DocuSign": "DocuSign for Startups: envelope credits or first-year % off.",
    "Firstbase": "Firstbase US company-formation credits/discounts.",
    "AngelList": "AngelList stack (fund admin / talent) benefits in some VC programs.",
    "Plaid": "Plaid for Startups: fintech API credits or fee discounts.",
    "Navan": "Navan (travel) credits for portfolio companies on some banking/spend partner pages.",
    "Instantly": "Instantly cold-email platform discounts (e.g. 50% off) in GTM perk lists — ignore page-level '$1M' marketplace totals.",
    "Crunchbase": "Crunchbase Pro discounts via partner catalogs.",
    "Attio": "Attio CRM startup discounts in modern GTM stacks.",
    "Customer.io": "Customer.io messaging discounts/credits via partner programs.",
    "Klaviyo": "Klaviyo for Startups: email/SMS platform discounts.",
    "SendGrid": "SendGrid (Twilio) email credits in developer stacks.",
    "Framer": "Framer for Startups: site-plan discounts or credits.",
    "Shopify": "Shopify for Startups extended trial / plan credit.",
    "Razorpay": "Razorpay for Startups (India): payment-processing benefits on partner pages.",
    "Alchemy": "Alchemy web3 node/API credits in crypto accelerator stacks.",
    "PitchBook": "PitchBook data-terminal access is occasionally listed as a portfolio research perk (not a typical SaaS coupon).",
    "Sentry": "Sentry error-monitoring credits or first-year discounts.",
}


def clean_offers(raw: str) -> str:
    parts = [p.strip() for p in (raw or "").split("|")]
    keep = []
    for p in parts:
        if not p or "See supporting" in p:
            continue
        if JUNK.search(p):
            continue
        if p not in keep:
            keep.append(p)
    return " | ".join(keep[:8])


def category_of(name: str) -> str:
    for cat, names in CATEGORIES.items():
        if name in names:
            return cat
    if name.startswith("Program support:"):
        return "Fund/accelerator program (non-vendor catalog)"
    return "Other tools seen on perk pages"


def main() -> None:
    with SRC.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stats = json.loads(STATS.read_text()) if STATS.exists() else {}

    vendor_rows = [r for r in rows if not r["vendor_or_perk"].startswith("Program support:")]
    program_rows = [r for r in rows if r["vendor_or_perk"].startswith("Program support:")]

    clean = []
    for r in vendor_rows:
        name = r["vendor_or_perk"]
        offers = clean_offers(r["offer_details"])
        detail = CANONICAL.get(name)
        if not detail:
            if offers:
                detail = f"Appears across partner perk pages. Observed terms: {offers}."
            else:
                detail = (
                    "Named on partner perk pages; public pages rarely publish a single standard coupon. "
                    "Eligibility is usually ‘portfolio / accelerator / alumni only’."
                )
        clean.append(
            {
                "category": category_of(name),
                "unique_perk": name,
                "details": detail,
                "observed_terms_on_pages": offers,
                "partner_pages_mentioning_it": r["partner_count"],
                "example_partners": r["example_partners"],
                "example_urls": r["example_urls"],
            }
        )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(clean[0].keys()))
        w.writeheader()
        w.writerows(clean)

    lines = []
    a = lines.append
    a("# Unique perks across partner perk pages")
    a("")
    a("Source file: `partner-perk-pages-MASTER.csv` (1,312 partner rows, 1,125 unique URLs).")
    a("")
    a("## What this is")
    a("")
    a(
        "Most rows in the master sheet are **not unique products**. They are VC/accelerator pages "
        "(or vendor ‘for Startups’ partner pages) that repeat the same underlying vendor programs. "
        "After visiting the live URLs, the unique perks are the **vendor programs and deal types** below."
    )
    a("")
    a("## Coverage")
    a("")
    a(f"- Partner rows in CSV: **{stats.get('source_rows', 1312)}**")
    a(f"- Unique URLs fetched: **{stats.get('unique_urls', 1125)}**")
    a(f"- HTTP fetch succeeded: **{stats.get('fetch_ok', '?')}**")
    a(f"- Fetch failed (404/403/timeout/DNS/SSL): **{stats.get('fetch_fail', '?')}**")
    a(f"- Unique vendor perks: **{len(vendor_rows)}**")
    a(
        f"- Additional fund pages that only describe ‘credits/perks/marketplace’ without naming a vendor in extractable text: **{len(program_rows)}**"
    )
    a("")
    a("Eligibility almost always means: **current/alumni portfolio of the named partner**, sometimes with a funding cap, employee cap, or application. Dollar figures collide across pages because many sites advertise the **whole marketplace total** (for example a16z Speedrun’s “$10M+ in free credits”) next to individual vendors.")
    a("")
    a("Full machine-readable table: `unique_perks_clean.csv`.")
    a("")

    grouped: dict[str, list] = {}
    for row in clean:
        grouped.setdefault(row["category"], []).append(row)

    order = list(CATEGORIES.keys()) + ["Other tools seen on perk pages"]
    for cat in order:
        items = grouped.get(cat) or []
        if not items:
            continue
        a(f"## {cat}")
        a("")
        items.sort(key=lambda x: -int(x["partner_pages_mentioning_it"]))
        for row in items:
            a(f"### {row['unique_perk']}")
            a("")
            a(row["details"])
            a("")
            if row["observed_terms_on_pages"]:
                a(f"- Observed on pages/notes: `{row['observed_terms_on_pages']}`")
            a(f"- Seen via **{row['partner_pages_mentioning_it']}** partner rows")
            partners = row["example_partners"].split("; ")
            a(f"- Example partners: {', '.join(partners[:8])}")
            a("")

    a("## Fund / accelerator pages without a named vendor catalog")
    a("")
    a(
        "Hundreds of funds only describe hands-on help (hiring, customer intros, office hours) "
        "or a private perk portal. These are **not unique vendor SKUs**. Examples of pages that "
        "do advertise a numeric stack without listing vendors in extractable HTML:"
    )
    a("")
    numeric_programs = []
    for r in program_rows:
        offers = clean_offers(r["offer_details"])
        if offers:
            numeric_programs.append((r["vendor_or_perk"].replace("Program support: ", ""), offers, r["example_urls"]))
    for name, offers, urls in numeric_programs[:40]:
        a(f"- **{name}**: {offers}")
        if urls:
            a(f"  - {urls.split('; ')[0]}")
    a("")
    a("## How to use this")
    a("")
    a(
        "If you are building a unified perk marketplace, treat each heading above as one SKU "
        "and treat the 1,312 CSV rows as **distribution partners / eligibility paths**, not as 1,312 different perks."
    )
    a("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_MD} ({OUT_MD.stat().st_size} bytes)")
    print(f"wrote {OUT_CSV} rows={len(clean)}")


if __name__ == "__main__":
    main()
