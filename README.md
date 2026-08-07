# RTOLookup

A reference site that decodes Indian vehicle number plates and RTO codes, with plain-English guides for common RTO processes (RC transfer, owner check, duplicate RC, NOC, address change).

Built with **Next.js 16** (App Router), self-hosted fonts, and programmatic SEO — one statically generated page per RTO code.

## Features

- **Programmatic SEO** — `/rto/[code]` generates one static page per RTO code via `generateStaticParams`, each with unique title, description, canonical, and FAQ/Breadcrumb structured data.
- **Dynamic OG images** — branded social cards per RTO code via `next/og`.
- **Structured data** — WebSite + SearchAction, Organization, BreadcrumbList, FAQPage, HowTo (JSON-LD).
- **Auto sitemap + robots** — generated from the data layer.
- **Accessibility** — WCAG 2.1 AA verified (axe-core, 0 violations).
- **HSRP number-plate design** — self-hosted Chakra Petch / Inter / JetBrains Mono, dark "tarmac" palette, road-lane motif.

## Develop

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production build
npm start        # serve production build
```

## Accessibility audit

```bash
npm start                 # in one terminal
node e2e/a11y-audit.mjs    # axe-core via headless Chrome
```

## Scaling the data

All pages, sitemap entries, internal links, and OG images derive from [`data/rtos.js`](data/rtos.js). Swap the array for the full ~1,400-code national dataset and everything regenerates automatically.

## Not affiliated

This is an independent reference resource. It is not affiliated with MoRTH or Parivahan. For official services, use [parivahan.gov.in](https://parivahan.gov.in).
