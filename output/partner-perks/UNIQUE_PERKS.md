# Unique perks across partner perk pages

Source file: `partner-perk-pages-MASTER.csv` (1,312 partner rows, 1,125 unique URLs).

## What this is

Most rows in the master sheet are **not unique products**. They are VC/accelerator pages (or vendor ‘for Startups’ partner pages) that repeat the same underlying vendor programs. After visiting the live URLs, the unique perks are the **vendor programs and deal types** below.

## Coverage

- Partner rows in CSV: **1312**
- Unique URLs fetched: **1125**
- HTTP fetch succeeded: **1005**
- Fetch failed (404/403/timeout/DNS/SSL): **120**
- Unique vendor perks: **139**
- Additional fund pages that only describe ‘credits/perks/marketplace’ without naming a vendor in extractable text: **211**

Eligibility almost always means: **current/alumni portfolio of the named partner**, sometimes with a funding cap, employee cap, or application. Dollar figures collide across pages because many sites advertise the **whole marketplace total** (for example a16z Speedrun’s “$10M+ in free credits”) next to individual vendors.

Full machine-readable table: `unique_perks_clean.csv`.

## Cloud & infrastructure

### Google Cloud

Google for Startups Cloud Program: often $2K–$100K+ in GCP credits; some accelerator/VC paths advertise up to ~$200K. Eligibility usually requires an official partner referral.

- Observed on pages/notes: `Up to $200,000 | up to $100k | up to US$100K | credits $5,000 | $650k in cloud credits | up to €100,000 credit | up to $25,000 | 0% Off`
- Seen via **115** partner rows
- Example partners: 3one4capital, A16Z, ACE.SG, AI Perks, Aalto, Aceleradora Midas, Alif, Andreessen Horowitz

### AWS

AWS Activate / portfolio credits: commonly up to $5K–$100K, and up to ~$200K on stronger Activate or VC-portfolio packages. Cloud credits, not cash.

- Observed on pages/notes: `credits up to $200K | Up to $200K | credits $5,000 | credits $50,000 | Credits Up to $350K | Up To $100k | up to $25k | up to $75k`
- Seen via **91** partner rows
- Example partners: AWS Activate, Activate, AddedVal.io, Astana Hub, Aurelia Ventures, Belle De Mai, Bessemer, BonBillo, Inc.

### DigitalOcean

DigitalOcean for Startups: typically $1K–$2.5K in credit on public partner pages; some programs list up to $100K for qualified startups.

- Observed on pages/notes: `$100,000 credit | Up to $250k in credits | $300 in credits | $100,000 in credits | Up to €100,000 | Up to $20,000 | 90% off | 50% off`
- Seen via **36** partner rows
- Example partners: ABC accelerator, Atento Capital, CB Capital, CodeBase, DigitalOcean, Dimension Mill, Endure cap, Factory Berlin

### Microsoft Azure

Microsoft for Startups / Azure credits: commonly $1K–$25K for early startups, with some funds advertising up to ~$100K–$250K Azure credits for portfolio companies.

- Observed on pages/notes: `credits up to $5,000 | up to $5,000 | Up to $250,000 | Credits $25,000 | Credits Up to $120K | up to $150,000 | up to $250,000 | credits up to $250k`
- Seen via **32** partner rows
- Example partners: Aalto, Astana Hub, Axel, Draper B1, Draper B1 VC, ERA, Eurasian Hub Ventures, FIR Capital

### Vercel

Vercel for Startups: partner catalogs commonly list about $5K–$30K in credits depending on the program tier.

- Observed on pages/notes: `$30,000 in credits | $25,000 in credits | $15,000 in credits | $12,000 in credits | $11,000 in credits | $10,000 in credits | Up to $300 in credits | up to $250k in credits`
- Seen via **27** partner rows
- Example partners: CRV, Datadog for Startups, Earlybird, FIR Capital, First Round Capital, FirstMark Capital, Huddle, Latitud

### Cloudflare

Cloudflare for Startups credits and plan upgrades.

- Observed on pages/notes: `up to $350k in credits | $100k in credits | 50% Off | up to $250k | up to $250,000 | 60% off | $1,000 in credits | Up to $100k in credits`
- Seen via **14** partner rows
- Example partners: Angel Invest, Cherry Ventures, Cloudflare for Startups, FounderPass, Meet Ventures, Orbit, Orbit Startups, PerkBeacon

### OVHcloud

OVHcloud startup credits appear in European partner catalogs (e.g. Angel Invest); amounts vary by program.

- Observed on pages/notes: `up to €100,000 | 30% Off | Up to €100,000 | €10,000 in credits | €25,000 in cloud credits | $5,000 in credits | Up to $100,000 in credits | Up to $20,000`
- Seen via **13** partner rows
- Example partners: Angel Invest, EIT Culture & Creativity, EuraTechnologies, Hard2beat, LVenture Group, SMU, STRT, Startup Lithuania

### Firebase

Firebase / Google credits often bundled with Google for Startups rather than a separate catalog.

- Observed on pages/notes: `up to €100,000 credit | up to $25,000 | credits up to $100,000, | $100,000 in credits | Up to $350,000 | up to $250,000 | up to $200,000 | up to $350,000`
- Seen via **8** partner rows
- Example partners: Dogpatch Labs, FIR Capital, FirstMark Capital, Foxmont Capita, Glasswing Ventures, Meet Ventures, STRT, Startup Valencia

### Supabase

Supabase for Startups: database credits in modern app stacks.

- Observed on pages/notes: `50% off | 10% off | $300 in credits | 20% off | credits Up to $100k | Up to $300 in credits`
- Seen via **8** partner rows
- Example partners: AI Nation, Build Up, Build Up Labs, Mercury, PerkBeacon, Solo Founders, Square Peg, StartupPerks

### Alchemy

Alchemy web3 node/API credits in crypto accelerator stacks.

- Observed on pages/notes: `up to US$100K`
- Seen via **7** partner rows
- Example partners: Appworks, Highland Europe, Paradigm, PerkBook, StartupPerks, StoryHouse, Xartup Fellowship

### Heroku

Heroku credits via older accelerator/cloud bundles.

- Seen via **3** partner rows
- Example partners: Render, Render Capital, StartupPerks

### Railway

Railway hosting credits in newer builder stacks.

- Seen via **3** partner rows
- Example partners: Render, Render Capital, Sunflower

### CoreWeave

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Founders Factory, Founders Factory Africa

### Fly.io

Fly.io credits in some partner perk lists.

- Seen via **2** partner rows
- Example partners: Render, Render Capital

## AI models & AI tools

### ElevenLabs

ElevenLabs for Startups / partner packs: commonly 40–70% off or character/credit grants (examples include ~$500–$12K credits or 12 months / tens of millions of characters on builder packages).

- Observed on pages/notes: `40% off | credits $500 | $1,000 in Credits | $500 in Credits | 12 free months | up to $2,000 | up to $120,000 | up to $50,000`
- Seen via **108** partner rows
- Example partners: 996 LAB, Aalto, Antler, Asif Ventures, Bits and Pretzels, BlitzAI, Build Up, Capx

### OpenAI

OpenAI API / ChatGPT credits via accelerators and VC marketplaces. Public partner pages range from a few thousand dollars up to much larger API credits on select programs; terms are invite/eligibility gated.

- Observed on pages/notes: `$7,500 in credits | Credits $3,600 | credit $1,500 | credits $500 | up to $150,000 | $10 credits | 50% off | 20% off`
- Seen via **78** partner rows
- Example partners: 351 Portuguese Startup Association, A16Z, ACE.SG, AI Perks, Andreessen Horowitz, Astana Hub, Beta University, Bits and Pretzels

### Anthropic

Anthropic/Claude API credits via partner stacks. Typical listed amounts are in the low thousands of dollars in credits; larger packages exist on select AI-focused programs.

- Observed on pages/notes: `$7,500 in credits | Credits $3,600 | credit $1,500 | credits $500 | 50% off | $2,500 in Credits | $500 in Credits | $50,000 in Credits`
- Seen via **43** partner rows
- Example partners: 996 LAB, A16Z, AI Perks, Andreessen Horowitz, BADideas.fund, Claude Startup Perks, Datadog for Startups, ERA

### NVIDIA

NVIDIA Inception: platform benefits, pricing, and sometimes cloud/GPU credits. Partner pages advertise anywhere from tens of thousands up to ~$150K–$350K in related credits depending on the program.

- Observed on pages/notes: `up to $350K | up to $150,000 | Up to $200,000 | up to $350,000 | $50,000 in Credits | $5,000 in Credits | $1,000 in Credits | $500 in Credits`
- Seen via **38** partner rows
- Example partners: A16Z, AI Nation, Andreessen Horowitz, Astana Hub, BOOST Accelerator, BTFV, Breakthrough VC, Carao

### Runway

Runway ML: credits or ~20–50% off; some catalogs list up to a few thousand dollars or larger European credit packs.

- Observed on pages/notes: `20% OFF | up to $3,400 | up to €90k | up to €25k | free for 6 months`
- Seen via **34** partner rows
- Example partners: AI Nation, Airtree, Aurelia Ventures, Avidbank, Berlin Innovation Agency, Bulletpitch, Campus Founders, Cherry Ventures

### Cursor

Cursor IDE/pro credits or discounts appear in several AI/accelerator perk lists (amounts rarely standardized publicly).

- Observed on pages/notes: `$2M credit`
- Seen via **13** partner rows
- Example partners: Datadog for Startups, Exa, First Round Capital, GoFloaters, ISB I-Venture, MIT delta v, Nat Friedman and Daniel Gross AI Grant, PeakXV

### Replicate

Replicate inference credits in AI perk aggregators and accelerator stacks.

- Observed on pages/notes: `$55,000 in credits | $50,000 in credits | $30,000 in credits | $25,000 in credits | $15,000 in credits | $12,000 in credits | $250k in credits | up to $100k in credits`
- Seen via **8** partner rows
- Example partners: Nat Friedman and Daniel Gross AI Grant, Perkstack, Seedblink, Sequoia, SocialTech Lab, StartupPerks, Sunflower, The Baobab Network

### Mistral AI

Mistral API credits via AI-focused partner stacks.

- Seen via **7** partner rows
- Example partners: FIR Capital, FirstMark Capital, Firstminutecapital, Perkstack, SpARK Labs, StartupPerks, StationF

### Cohere

Cohere API credits via partner/AI programs.

- Observed on pages/notes: `$10,000 in credits | 10 free seats | 25% off | 20% off | $7,500 in credits | $5,000 in credits`
- Seen via **6** partner rows
- Example partners: FIR Capital, FirstMark Capital, Nat Friedman and Daniel Gross AI Grant, S32, StartupPerks, Sunflower

### Hugging Face

Hugging Face Pro/hardware or inference credits via AI startup programs.

- Observed on pages/notes: `up to $2,000 | up to $120,000 | up to $50,000 | $12,000 in credits | $11,000 in credits | $10,000 in credits | 10 free seats`
- Seen via **6** partner rows
- Example partners: MBZUAI, Nat Friedman and Daniel Gross AI Grant, StartupPerks, Station F, StationF, Titan Capital

### Perplexity

Perplexity enterprise/API credits in some AI perk lists.

- Observed on pages/notes: `$2,500 in Credits | $500 in Credits | $50,000 in Credits | $5,000 in Credits | 20% off | $10,000 in credits | 10 free seats | 25% off`
- Seen via **6** partner rows
- Example partners: Founders Inc., Nat Friedman and Daniel Gross AI Grant, ODDBIRD, Paradigm, ParentPreneur Foundation, Pareto

### Pinecone

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **3** partner rows
- Example partners: Datadog for Startups, Italian Founders Fund, StartupPerks

### Google Gemini

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Paradigm, The Ventures

### Midjourney

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Nat Friedman and Daniel Gross AI Grant, Soma Capital

### Together AI

Appears across partner perk pages. Observed terms: 10 free seats | 25% off | 20% off | $7,500 in credits | $5,000 in credits | $2,500 in credits.

- Observed on pages/notes: `10 free seats | 25% off | 20% off | $7,500 in credits | $5,000 in credits | $2,500 in credits`
- Seen via **2** partner rows
- Example partners: Nat Friedman and Daniel Gross AI Grant, StartupPerks

### Weaviate

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Datadog for Startups, StartupPerks

### Qdrant

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: Datadog for Startups

## CRM, marketing & support

### HubSpot

HubSpot for Startups: most commonly up to 90% off year one for eligible early startups (often <~$2M raised or accelerator/alumni status); larger companies may see ~50% off. Some pages also mention HubSpot credits.

- Observed on pages/notes: `90% off | 50% off | 25% off | credits $5,000 | 90% Off | €15,000 Credits | 75% off | 20% off`
- Seen via **148** partner rows
- Example partners: 351 Portuguese Startup Association, AG Startup Engine, AI Nation, Accelerating Asia, Afore, Alif, Amplify, Angel Invest

### Zendesk

Zendesk for Startups: typically first-month or first-year discounts (examples: 10% off first month, up to ~75–90% off year one) plus occasional credits.

- Observed on pages/notes: `up to US$100K | 90% off | 15% off | $1,000 in free credits | 10% off first month | 75% off | $15,000 credits | 30-day trial`
- Seen via **77** partner rows
- Example partners: 351 Portuguese Startup Association, Accelerating Asia, Amplify, Appworks, Ascension, Axel, Build Up, Build Up Labs

### Instantly

Instantly cold-email platform discounts (e.g. 50% off) in GTM perk lists — ignore page-level '$1M' marketplace totals.

- Observed on pages/notes: `50% off`
- Seen via **44** partner rows
- Example partners: Acrobator Ventures, Alven, Ampolon Ventures, Attio, Axel, BuiltFirst Technologies, Inc, CIC, Catchin

### Intercom

Intercom / Fin startup packs: free or heavily discounted first year (examples include free for 1 year, 25–100% off, or bundled $500K+ partner-deal access on some pages).

- Observed on pages/notes: `free for 1 year | up to $25,000 | 100% off | 50% off | 25% off | 95% Off | 20% off | 100% off 1st Year`
- Seen via **29** partner rows
- Example partners: AI Perks, Angel Invest, Attio, Builtfirst, Dogpatch Labs, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com)

### Salesforce

Salesforce for Startups: trial plus substantial first-year discounts (partner pages cite ~50–90% off subject to eligibility).

- Observed on pages/notes: `14 day free trial | 50% off | 90% off`
- Seen via **27** partner rows
- Example partners: Alchemist Accelerator, Attio, B4i - Bocconi for innovations, Builtfirst, Catchin, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com)

### Freshworks

Freshworks for Startups: CRM/support suite discounts via partner programs.

- Observed on pages/notes: `up to $10000 in credits | $1000 in credits | 14 day free trial | 50% off | $1000 in free credits | $1k credit | 90% off | $5,000 credits`
- Seen via **21** partner rows
- Example partners: Builtfirst, DEPO Ventures, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, First Cheque, GSVlabs

### Pipedrive

Pipedrive for Startups: substantial first-year % off on several partner pages.

- Observed on pages/notes: `up to $12,000 | 30 day free trial | 30 Day Trial | 20% Off | 30% off | up to $1579`
- Seen via **18** partner rows
- Example partners: AI Nation, Antler, Attio, Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital

### DocSend

Appears across partner perk pages. Observed terms: 90% off | 20% off | 15% off | 70% off.

- Observed on pages/notes: `90% off | 20% off | 15% off | 70% off`
- Seen via **16** partner rows
- Example partners: Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, FIR Capital, FirstMark Capital, Founderland, Founderscard

### Crunchbase

Crunchbase Pro discounts via partner catalogs.

- Observed on pages/notes: `90% off | 30% off | 20% OFF`
- Seen via **11** partner rows
- Example partners: Acurio Ventures, Angel Invest, B4i - Bocconi for innovations, Exa, Flat6 Labs, Go Global World (GGW), Liquid2, PerkBeacon

### Customer.io

Customer.io messaging discounts/credits via partner programs.

- Observed on pages/notes: `credits $50,000 | 50% off | 80% off | 90% off | up to $5,000. | 100% off`
- Seen via **11** partner rows
- Example partners: Aurelia Ventures, BlitzAI, Earlybird, Founders Inc., M Accelerator, Novapuls, Peak Capital, Platvix

### Hotjar

Appears across partner perk pages. Observed terms: 20% off | 80% off | up to $50,000 | 90% off | 25% off | 20% OFF | 90 Day Free Trial | 60% OFF.

- Observed on pages/notes: `20% off | 80% off | up to $50,000 | 90% off | 25% off | 20% OFF | 90 Day Free Trial | 60% OFF`
- Seen via **10** partner rows
- Example partners: Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, GSVlabs, OneValley, Peak Capital

### Unbounce

Appears across partner perk pages. Observed terms: up to $10M | 35% off | 14-day free trial | up to $560 | 10% Off.

- Observed on pages/notes: `up to $10M | 35% off | 14-day free trial | up to $560 | 10% Off`
- Seen via **6** partner rows
- Example partners: Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, Startup Wise Guys

### Attio

Attio CRM startup discounts in modern GTM stacks.

- Observed on pages/notes: `50% off | 80% off | 90% off | 30% off`
- Seen via **4** partner rows
- Example partners: Attio, Builtfirst, Founders Inc., Startuplist

### Mailchimp

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **4** partner rows
- Example partners: Attio, Peak Capital, Pentathlon Ventures, StartupPerks

### Klaviyo

Klaviyo for Startups: email/SMS platform discounts.

- Seen via **3** partner rows
- Example partners: Glasswing Ventures, MIT delta v, RevRoad

### Braze

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: GTM Fund, Tech for Black Founders

### FullStory

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: M Accelerator, Tech for Black Founders

### Lemlist

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Bits and Pretzels, Novapuls

### Clearbit

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: Startup Credits

## Payments, banking & spend

### Stripe

Stripe for Startups / Atlas: fee waivers or credits (examples: ~$20K Atlas-style credits, 90% off Atlas on some packs) plus payment processing — not cloud GPU credits.

- Observed on pages/notes: `up to US$100K | credits $50,000 | 90% Off | €15,000 Credits | $3,000 Credits | Credits Up to $120K | $7,500 in credits | Credits $3,600`
- Seen via **96** partner rows
- Example partners: A16Z, Accelerating Asia, AddedVal.io, Andreessen Horowitz, Angel Investment Network Ltd, Ansa, Appworks, Ascension

### Ramp

Ramp for Startups: corporate cards, 1.5%+ cashback style rewards, and partner credits (public pages mention ~$1.5K–$5K+ credits or larger ‘up to $250K’ marketplace-style packages on some VC pages).

- Observed on pages/notes: `20% off | credits up to $250k | $350K credits | up to $351,000 | 20% Off | up to $5,000 | 20% off first year`
- Seen via **82** partner rows
- Example partners: 46 VC, 46 Venture Capital, AEA, Acrobator Ventures, Alven, Ampolon Ventures, Arthur Ventures, BTFV

### Brex

Brex for Startups: founder banking/card perks — credits, fee-free accounts, and sometimes 30–50% off first-year services. Amounts like $5K credits appear on several partner pages.

- Observed on pages/notes: `up to $5,000 | 50% off the first year | 30% off | 50% off | 10% off | up to $3,996 | 20% off first year | Up to $5k in credits`
- Seen via **32** partner rows
- Example partners: Brex, Builtfirst, Carao, Day Zero, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital

### Rho

Rho treasury/banking for portfolio companies: metal cards, statement credits (examples: $1.6K–$4K credits, Pods, travel/hardware gifts). Not a SaaS discount catalog.

- Observed on pages/notes: `$3k credit | $1,600 credit | $4,000 credit`
- Seen via **24** partner rows
- Example partners: 468 Capital, 8VC, Correlation VC, Decibel VC/Partners, Fintech Collective, Flex Capital, Floodgate, Flybridge

### Airwallex

Airwallex for Startups: fee waivers on FX/payments plus bundled partner credits.

- Observed on pages/notes: `fee waivers | $400 free credits | 15% off | up to $100, | up to $100,000. | up to $5000 | up to £120k`
- Seen via **16** partner rows
- Example partners: ACE.SG, Airwallex, BTFV, FIR Capital, FirstMark Capital, Folklore Ventures, FounderPass, Gold Coast Innovation Hub

### Mercury

Mercury banking perks for venture-backed startups (priority onboarding, credits, sometimes partner software credits).

- Observed on pages/notes: `50% off | 80% off | 90% off | Up to $5k in credits | Up to $2k in credits | Up to $300 in credits | $1M in credits`
- Seen via **15** partner rows
- Example partners: Attio, CRV, ERA, Earlybird, FIR Capital, FirstMark Capital, Forecastr, Founders Inc.

### Stripe Atlas

Stripe Atlas company-formation discount/credits for eligible startups via partner programs.

- Observed on pages/notes: `Up to $5,000 | Up to $2k in credits | 90% off | 20% off | 93% off`
- Seen via **10** partner rows
- Example partners: ITU ARI Teknokent, Nat Friedman and Daniel Gross AI Grant, ODF, On Deck, PerkBeacon, SaaSOffers, Startup Credits, StartupPerks

### Razorpay

Razorpay for Startups (India): payment-processing benefits on partner pages.

- Observed on pages/notes: `up to $100k | $100k credit | Free for 3 months | $1000 in free credits | $1k credit | 90% off | $5,000 credits`
- Seen via **8** partner rows
- Example partners: 3one4capital, First Cheque, ISB I-Venture, PIEDS BITS Pilani, RazorPay, Razorpay Rize, Razorpay Software Private Limited, SMU

### Pleo

Pleo spend cards: partner pages advertise up to ~33% off or ~1% cashback for eligible VC portfolios.

- Observed on pages/notes: `33% off`
- Seen via **7** partner rows
- Example partners: 10x Founders, BuildersNetwork, Creandum, IBB Ventures, Picus Capital, STS Ventures, Techquartier

### Navan

Navan (travel) credits for portfolio companies on some banking/spend partner pages.

- Seen via **5** partner rows
- Example partners: Builtfirst, FIR Capital, FirstMark Capital, Mucker Capital, Project A

### Plaid

Plaid for Startups: fintech API credits or fee discounts.

- Observed on pages/notes: `$7,500 in credits | Credits $3,600 | credit $1,500 | credits $500`
- Seen via **5** partner rows
- Example partners: Builtfirst, ERA, RevRoad, Silicon Valley Bank, StartupPerks

### Payoneer

Appears across partner perk pages. Observed terms: 20% OFF | 10% OFF.

- Observed on pages/notes: `20% OFF | 10% OFF`
- Seen via **3** partner rows
- Example partners: Go Global World (GGW), Velocity Capital, Velocity Fund

### Expensify

Appears across partner perk pages. Observed terms: 30% off | 50% OFF.

- Observed on pages/notes: `30% off | 50% OFF`
- Seen via **2** partner rows
- Example partners: GSVlabs, OneValley

## HR, payroll, EOR & talent

### Deel

Deel for Startups: free seats and EOR/payroll discounts for companies referred by a VC/accelerator partner. Public pages mention free seats, ~10 free EOR, credits around $5K–$6K, or large % off — terms are partner-specific.

- Observed on pages/notes: `95% Off | Up to $6,000 | $5,000 free credits | 10 free seats | 25% off | 20% off | $7,500 in credits | $5,000 in credits`
- Seen via **141** partner rows
- Example partners: 100x VC, 1909 Foundation, 1982 Ventures, 20VC, 360 Capital, 401 Accelerator, A16Z, APX

### RemoFirst

RemoFirst EOR: commonly 30–50% off plus 1–2 months free for partner-backed startups; some pages mention a first-month fee waiver.

- Observed on pages/notes: `50% off | fee waiver`
- Seen via **29** partner rows
- Example partners: BITKRAFT Ventures, Balderton, Bitkraft, Blumberg Capital, Bread and Butter Ventures, Brighton Park Capital, Builtfirst, Burnt Island Ventures

### Rippling

Rippling HR/IT/finance stack discounts via partner programs (often first-year % off; some pages bundle 50+ software deals).

- Observed on pages/notes: `90% off`
- Seen via **20** partner rows
- Example partners: Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, FIR Capital, First Round Capital, FirstMark Capital

### Gusto

Gusto payroll discounts for startups via VC/accelerator partner pages.

- Observed on pages/notes: `up to $200 | $5k credits | 50% off | 25% Off | 30% OFF | 20% OFF | up to $10,000`
- Seen via **17** partner rows
- Example partners: Antler, Builtfirst, Character VC, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, GSVlabs

### Greenhouse

Greenhouse ATS discounts for venture-backed hiring teams.

- Seen via **9** partner rows
- Example partners: Climate Collective Foundation, Elemental Excelerator, FIR Capital, FirstMark Capital, Glasswing Ventures, Imperial Enterprise Lab, Investible, SMU

### Lattice

Lattice HR/performance discounts via partner programs.

- Observed on pages/notes: `up to $560 | 10% Off | Up to $2,000 | 10% OFF`
- Seen via **8** partner rows
- Example partners: Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, Glasswing Ventures, Go Global World (GGW), Startup Wise Guys

### Justworks

Justworks PEO discounts on selected partner pages.

- Observed on pages/notes: `$1k Credit | $3.6K Credits`
- Seen via **4** partner rows
- Example partners: Builtfirst, ERA, Outliers Summit, Visible Hands

### Ashby

Ashby ATS startup pricing via partner introductions.

- Observed on pages/notes: `20% off first year | 10% off | 20% off | 50% off first year`
- Seen via **3** partner rows
- Example partners: FIR Capital, FirstMark Capital, Founders Inc.

### AngelList

AngelList stack (fund admin / talent) benefits in some VC programs.

- Observed on pages/notes: `$500 Credit | $1k Credit`
- Seen via **2** partner rows
- Example partners: Outliers Summit, Visible Hands

### Personio

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Cherry Ventures, WE.VESTR

### HiBob

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: Antler

## Insurance, legal & cap table

### Vouch

Vouch Insurance: venture-ready startup insurance (D&O, E&O, cyber, etc.) for named VC portfolios. This is an insurance product path, not AWS-style credits.

- Observed on pages/notes: `$250K+ in cloud credits | $1,000 in free credits | 50% off | $3k credit | $1k Credit | $3.6K Credits | 20% off | up to $5,000`
- Seen via **102** partner rows
- Example partners: 645 Ventures, Agya Ventures, Allegis Capital, Angular Ventures, Anthemis, Base10, Berkeley Skydeck, Big Idea Ventures

### Carta

Carta cap-table / equity management: commonly ~10–25% off the first year (some pages 20% off first year) for partner-backed companies.

- Observed on pages/notes: `20% off first year | 20% off | 10% OFF | 20% OFF | 25% off | up to $50,000 in credits | 80% off`
- Seen via **34** partner rows
- Example partners: 1752vc, ACE.SG, Amity VC, Axel, Builtfirst, Carta, Diagram Ventures, ERA

### Pilot

Pilot bookkeeping: startup credits (examples $1K–$10K) or ~25% off via partner programs.

- Observed on pages/notes: `20% off | $7,000 in credits | 10% off`
- Seen via **9** partner rows
- Example partners: Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, FIR Capital, FirstMark Capital, Mento Ventures

### DocuSign

DocuSign for Startups: envelope credits or first-year % off.

- Observed on pages/notes: `15% Off | 10% off`
- Seen via **4** partner rows
- Example partners: Builtfirst, FIR Capital, FirstMark Capital, SaaSOffers

### Firstbase

Firstbase US company-formation credits/discounts.

- Observed on pages/notes: `10% OFF | 20% OFF`
- Seen via **2** partner rows
- Example partners: Builtfirst, Go Global World (GGW)

### Ravio

Ravio compensation benchmarks: example partner offer is a 60-day free trial (for 100+ employees) or 15% off the first year, plus free benchmarks.

- Observed on pages/notes: `60-day free trial | 15% off first year | 5 free benchmarks`
- Seen via **1** partner rows
- Example partners: 13 Books Capital

## Dev tools, data & observability

### GitHub

GitHub for Startups: typically up to ~$10K in GitHub Enterprise/Actions credits via official ecosystem partners (many CSV rows are GitHub partner listing pages, not independent dealbooks).

- Observed on pages/notes: `$10k credits | up to $10,000 | free for 1 year | Up to $10K | $10k in credits | up to $300,000 in credits | 50% off | 25% off`
- Seen via **130** partner rows
- Example partners: 2bX, 351 Portuguese Startup Association, 4Founders Capital, 6AM Accelerator, 866 studios, AI Nation, Aceleratec POWERED BY SOLYDES + UPB, Advanced Technology Development Center

### MongoDB

MongoDB for Startups: credits commonly advertised around $5K–$50K plus a trial; some AI stacks list additional credits.

- Observed on pages/notes: `credits $5,000 | credits $50,000 | 30 Day Trial | 20% Off | $7,500 in credits | Credits $3,600 | credit $1,500 | credits $500`
- Seen via **41** partner rows
- Example partners: AI Nation, Aurelia Ventures, Basis Set, Build Up, Build Up Labs, Builtfirst, CBIT Venture Builder, D11z

### Datadog

Datadog for Startups: monitoring credits often listed around $50K–$100K, with some programs up to ~$250K–$500K.

- Observed on pages/notes: `up to $100k in credits | up to $100k | up to $500k | up to $350k in credits | up to $250k in credits | up to $75k | $30k in credits | free for 1 year`
- Seen via **26** partner rows
- Example partners: Acrobator Ventures, Alven, Ampolon Ventures, Connect Ventures, Contrary Ventures, Datadog for Startups, Dubai Future District Fund, EVCA

### Sentry

Sentry error-monitoring credits or first-year discounts.

- Observed on pages/notes: `20% off 1st year | $50,000+ in free credits`
- Seen via **22** partner rows
- Example partners: Acrobator Ventures, Alven, Ampolon Ventures, Attio, Connect Ventures, Contrary Ventures, Dubai Future District Fund, EVCA

### GitHub Copilot

GitHub Copilot discounts or free months (examples: 80% off, free for 6 months) when bundled in GitHub for Startups or accelerator stacks.

- Observed on pages/notes: `10% Off | free for 6 months | 80% off`
- Seen via **21** partner rows
- Example partners: BTFV, Builtfirst, Capria VC, Cherry Ventures, Futurelist, Google For Startups, Hard2beat, Impact Sprint Lab

### Mixpanel

Mixpanel for Startups: first-year discounts or credits via VC/accelerator partners.

- Observed on pages/notes: `credits $5,000 | credits $50,000 | $50,000 Credits | free 6 months | 20% off | 80% off | up to $50,000 | 90% off`
- Seen via **20** partner rows
- Example partners: Aurelia Ventures, Carao, Draper B1, Draper B1 VC, Entrepreneurs Collective, Glasswing Ventures, Go Global World (GGW), Lighthouse Ventures

### Resend

Resend email API: partner catalogs list credits in the hundreds to low thousands of dollars.

- Seen via **20** partner rows
- Example partners: Acrobator Ventures, Alven, Ampolon Ventures, Connect Ventures, Contrary Ventures, Dubai Future District Fund, EVCA, Element Ventures

### Amplitude

Amplitude for Startups: credits/discounts in partner stacks.

- Observed on pages/notes: `$500 in Credits | 50% off | 80% off | 90% off`
- Seen via **15** partner rows
- Example partners: Builtfirst, Earlybird, Flyer One Ventures, Forecastr, Founders Inc., Hustle Fund, M Accelerator, Peak Capital

### PostHog

PostHog for Startups: product-analytics credits commonly $500–$50K depending on partner tier.

- Observed on pages/notes: `$2,500 in Credits | $500 in Credits | $50,000 in Credits | $5,000 in Credits | 20% off | up to $2,000 | up to $120,000 | up to $50,000`
- Seen via **14** partner rows
- Example partners: Alif, Build Up, Builtfirst, Founders Inc., Glasswing Ventures, MBZUAI, MIT delta v, Nat Friedman and Daniel Gross AI Grant

### Twilio

Twilio / Segment startup credits (Segment pages mention up to ~$50K) plus communications credits in accelerator stacks.

- Observed on pages/notes: `up to US$100K | up to $50,000 | up to $1M | $1k Credit | $500 Credit | up to $5M`
- Seen via **13** partner rows
- Example partners: Appworks, Dogpatch Labs, Fintech Wales Foundry Accelerator, Gold Coast Innovation Hub, M Accelerator, Novapuls, RevRoad, ScOP VC

### Algolia

Algolia for Startups: search credits via partner catalogs.

- Observed on pages/notes: `$10,000 in credits`
- Seen via **12** partner rows
- Example partners: Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, PerkBook, SaaSOffers, Standard Capital

### Databricks

Databricks for Startups: platform credits in data/AI partner stacks.

- Observed on pages/notes: `$400 free credits | up to €100k | up to $50k | up to $50K in credits`
- Seen via **11** partner rows
- Example partners: Aceleradora Midas, Bits and Pretzels, Builtfirst, Credo Ventures, FounderPass, S32, SF IRL, ScOP VC

### Snowflake

Snowflake startup credits (data-cloud) via partner/VC programs.

- Seen via **10** partner rows
- Example partners: Ansa, FIR Capital, FirstMark Capital, GTM Fund, Graduate Ventures, ICONIQ, Nat Friedman and Daniel Gross AI Grant, StartupPerks

### SendGrid

SendGrid (Twilio) email credits in developer stacks.

- Observed on pages/notes: `up to $1M | $1k Credit | $500 Credit`
- Seen via **9** partner rows
- Example partners: GAN, GSVlabs, M Accelerator, SaaSOffers, Segment, StartupPerks, Velocity Capital, Velocity Fund

### Okta

Okta for Startups: identity-platform discounts (pages mention ~10% off or credits in the low thousands).

- Observed on pages/notes: `up to $2,100`
- Seen via **7** partner rows
- Example partners: Builtfirst, Burnt Island Ventures, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, Startup Wise Guys

### Auth0

Auth0 for Startups: free tier expansion / credits via partner programs.

- Observed on pages/notes: `95% Off | Free for 1 Year | $1k Credit | $3.6K Credits`
- Seen via **6** partner rows
- Example partners: FounderPass, Latitud, Render, Render Capital, StartupPerks, Visible Hands

### GitLab

Appears across partner perk pages. Observed terms: free for 1 year.

- Observed on pages/notes: `free for 1 year`
- Seen via **5** partner rows
- Example partners: Ansa, Grantify, StartupPerks, Techleap, Vermilion

### Grafana

Appears across partner perk pages. Observed terms: Up to $100,000.

- Observed on pages/notes: `Up to $100,000`
- Seen via **4** partner rows
- Example partners: HV Capital, Icebreaker.vc., SaaSOffers, StartupPerks

### Bitbucket

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: The Factory NZ

### CircleCI

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: StartupPerks

### Cloudinary

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: StartupPerks

### Mailgun

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: StartupPerks

### New Relic

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: StartupPerks

### Postmark

Appears across partner perk pages. Observed terms: Free 12 months.

- Observed on pages/notes: `Free 12 months`
- Seen via **1** partner rows
- Example partners: StartupPerks

## Productivity, collab & design

### Notion

Notion for Startups: plus/enterprise credits and % off. Public partner mentions include ~$1K–$12K credits, 6 months free, or 10–50% off depending on program.

- Observed on pages/notes: `up to $12,000 | credits $50,000 | $50,000 Credits | free 6 months | up to $25,000 | 50% off | 10% off | up to $3,996`
- Seen via **117** partner rows
- Example partners: 2048 Ventures, 351 Portuguese Startup Association, 53 Stations, ACE.SG, Aalto, Airtree, Alif, Angel Investment Network Ltd

### Slack

Slack for Startups: typically ~50% off the first year (some catalogs 20–79% off or credits) for eligible early-stage companies.

- Observed on pages/notes: `25% Off | 20% off | Up to $9000 | credits up to $250k | 50% off | 79% OFF | 90% off | 25% off`
- Seen via **60** partner rows
- Example partners: 2048 Ventures, Amity VC, Angel Invest, Attio, Basis Set, Bethnal Green Ventures, Bonfire Ventures, Build Club

### Miro

Miro for Startups: credits or 30–50%+ off (partner pages also mention $1K–$10K credits).

- Observed on pages/notes: `up to $5,000 | $1,000 in credit | $1,000 in credits | 30% off | up to $10k | 90% off | 50% off | 100% off`
- Seen via **59** partner rows
- Example partners: 351 Portuguese Startup Association, AI Nation, Aalto, AddedVal.io, AltaIR Capital, Attio, Axel, BS Innovation Hub

### Webflow

Webflow for Startups: 12 months free or credits often listed around $9K–$12K, with some catalogs up to $100K.

- Observed on pages/notes: `Up to $12k in credits | 12 free months | up to $100k | credits $25k | $100k credits | $100k credit | Free for 3 months | $1000 in free credits`
- Seen via **34** partner rows
- Example partners: Acrobator Ventures, Alven, Ampolon Ventures, Antler, Connect Ventures, Contrary Ventures, Dubai Future District Fund, EVCA

### Airtable

Airtable for Startups: credits (examples ~$1K) and large % off on some marketplace pages.

- Observed on pages/notes: `$1,000 in free credits | $7,500 in credits | Credits $3,600 | credit $1,500 | credits $500 | 90% OFF | $2,000+ in Cloud Credits | 10% OFF`
- Seen via **27** partner rows
- Example partners: Angel Investment Network Ltd, Atlantic Labs & FoodLabs, Builtfirst, ERA, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrepreneurship Cell, IIT Kharagpur

### Shopify

Shopify for Startups extended trial / plan credit.

- Seen via **19** partner rows
- Example partners: Amity VC, Antler, Envision Accelerator, First Round Capital, Gold House, Gold House Ventures, KRING, Microtraction

### Canva

Canva for Startups / nonprofit-style discounts via some partner catalogs.

- Seen via **18** partner rows
- Example partners: Airtree, Block Dojo, Entrepreneurs Collective, Entrepreneurship Cell, IIT Kharagpur, First Round Capital, Founders Factory, Founders Factory Africa, Growth Mentor

### Asana

Asana for Startups: first-year discounts.

- Observed on pages/notes: `6 free months | 25% off | 30% off | 80% off | $5k credits | 20% off | 70% off | 100% off`
- Seen via **14** partner rows
- Example partners: Catchin, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, Glasswing Ventures, Hard2beat, Imperial Enterprise Lab

### Atlassian

Atlassian Cloud for Startups: typically 1 year free of Standard cloud products then a discount year, subject to eligibility.

- Observed on pages/notes: `free for 12 months | FREE for 12 months | up to $30,000 | 30% off | 25% off | up to $100,000.`
- Seen via **14** partner rows
- Example partners: Ansa, Catchin, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, Forecastr, ISB I-Venture

### Typeform

Typeform for Startups: first-year % off via partner catalogs.

- Observed on pages/notes: `75% off | 50% off | 80% off | 90% off | 25% off`
- Seen via **13** partner rows
- Example partners: Aalto, Attio, Expert Dojo, FIR Capital, FirstMark Capital, Founders Inc., ParentPreneur Foundation, SaaStock

### Figma

Figma for Startups: complimentary seats / first-year discounts via official startup and VC programs.

- Observed on pages/notes: `free for 6 months`
- Seen via **12** partner rows
- Example partners: Basis Set, Huddle, Imperial Enterprise Lab, MIT delta v, Nat Friedman and Daniel Gross AI Grant, Perkstack, SaaSOffers, Scaleway

### Google Workspace

Google Workspace for Startups: often 12 months free / discounted seats via Google for Startups partners.

- Observed on pages/notes: `20% off | Up to $100k | Up to $350,000 | $5k credits | 50% off | 25% Off | Free 3 Months | up to $350k`
- Seen via **12** partner rows
- Example partners: Bridge for Billions, FIR Capital, FirstMark Capital, FounderPass, Glasswing Ventures, ISB I-Venture, Mercury, NachoNacho

### ClickUp

ClickUp for Startups: first-year discounts.

- Observed on pages/notes: `credits $50,000 | 90% off | 20% off | 25% OFF | 20% OFF | 75% off`
- Seen via **11** partner rows
- Example partners: Aurelia Ventures, Go Global World (GGW), Komunite, NachoNacho, Nucleus Ventures, PIEDS BITS Pilani, STRT, SaaSOffers

### WeWork

WeWork for Startups: membership credits or discounts (often inside European VC marketplaces).

- Observed on pages/notes: `$1,000 in free credits | 30% off first year | 50% Off | 25% off first month | 30% off | 15% off | 15% OFF`
- Seen via **10** partner rows
- Example partners: Angel Invest, Builtfirst, Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, GrowthX, Loyal VC

### Xero

Xero accounting discounts for startups via partner pages.

- Observed on pages/notes: `90% off | 15% Off | 95% Off | 20% off | 95% off | 79% OFF | 6 free months | 25% off`
- Seen via **10** partner rows
- Example partners: Antler, Builtfirst, FounderPass, Go Global World (GGW), Mercury, Outward, Outward VC, Stripe Atlas

### QuickBooks

QuickBooks for Startups: first-year % off.

- Observed on pages/notes: `$5k credits | 50% off | 25% Off | 15% off first year`
- Seen via **9** partner rows
- Example partners: Earlybird, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, Mercury, Startup Wise Guys, Supercharger Ventures, WEtech Alliance

### monday.com

monday.com for Startups: first-year discounts.

- Observed on pages/notes: `30% off`
- Seen via **8** partner rows
- Example partners: Ada Ventures, Base44, BlitzAI, Entrepreneur First, Entrepreneur First (joinef.com), Entrée Capital, SaaSOffers, Startuplist

### Framer

Framer for Startups: site-plan discounts or credits.

- Observed on pages/notes: `20% off | 90% off | $1,000 in Credits | $500 in Credits | $50,000 in credits | 25% off`
- Seen via **7** partner rows
- Example partners: BlackCube Labs, FounderPass, Founders Inc., Huddle, Startuplist, Vento, With SAM

### Loom

Loom for Startups: credits or % off via partner catalogs.

- Observed on pages/notes: `up to $50,000 | 90% off | 25% off | 75% off`
- Seen via **7** partner rows
- Example partners: Long Journey, Outliers Summit, PerkBeacon, Reaktorx, StartupPerks, Startupbootcamp Australia, The Factory NZ

### Microsoft 365

Microsoft 365 seats sometimes bundled with Microsoft for Startups.

- Observed on pages/notes: `15% Off | 10% Off`
- Seen via **6** partner rows
- Example partners: Builtfirst, Claude Startup Perks, Menlo, Microsoft Founders Hub, Microsoft for Startups, NachoNacho

### PitchBook

PitchBook data-terminal access is occasionally listed as a portfolio research perk (not a typical SaaS coupon).

- Observed on pages/notes: `90% off | 30% off`
- Seen via **6** partner rows
- Example partners: 757 Startups, Aalto, Imperial Enterprise Lab, MongoDB for Startups, PerkBeacon, Redbud VC

### Zapier

Zapier for Startups: task credits or plan discounts.

- Observed on pages/notes: `90% off`
- Seen via **6** partner rows
- Example partners: 1752vc, Amity VC, Attio, Builtfirst, NachoNacho, Redbud VC

### 1Password

1Password for Startups: team-plan discounts / credits.

- Observed on pages/notes: `30 day free trial | 14 day free trial | 10% OFF | 20% OFF | Up to $600 | 50% off`
- Seen via **4** partner rows
- Example partners: Antler, Go Global World (GGW), PerkBook, SpinLab – The HHL Accelerator

### Superhuman

Superhuman founder discounts in selected VC stacks.

- Seen via **3** partner rows
- Example partners: Rackhouse, Rackhouse VC, Village Global

### Affinity

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Blueprint, Investible

### Calendly

Calendly for Startups: first-year discounts.

- Seen via **2** partner rows
- Example partners: SaaStock, Vowel

### Contentful

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Ansa, First Momentum Ventures

### Fastly

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Sozo, StartupPerks

### Grammarly

Grammarly Business discounts in some partner catalogs.

- Seen via **2** partner rows
- Example partners: Gold House, Gold House Ventures

### NetSuite

Appears across partner perk pages. Observed terms: up to $10 | 15% OFF.

- Observed on pages/notes: `up to $10 | 15% OFF`
- Seen via **2** partner rows
- Example partners: Go Global World (GGW), Silicon Valley Bank

### Riverside

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: BFA Global - Catalyst Fund, Fabric Ventures

### ZoomInfo

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **2** partner rows
- Example partners: Exa, Sozo

### Backblaze

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: RAISE Summit

### Namecheap

Appears across partner perk pages. Observed terms: $5k credits | 50% off | 25% Off.

- Observed on pages/notes: `$5k credits | 50% off | 25% Off`
- Seen via **1** partner rows
- Example partners: Mercury

### Squarespace

Named on partner perk pages; public pages rarely publish a single standard coupon. Eligibility is usually ‘portfolio / accelerator / alumni only’.

- Seen via **1** partner rows
- Example partners: Five Elms Capital

## Fund / accelerator pages without a named vendor catalog

Hundreds of funds only describe hands-on help (hiring, customer intros, office hours) or a private perk portal. These are **not unique vendor SKUs**. Examples of pages that do advertise a numeric stack without listing vendors in extractable HTML:

- **Blue Startups**: up to $1m
  - https://www.bluestartups.com/apply/
- **Comma Capital**: 25% off first year
  - https://f4.fund/firms/comma-capital
- **Craft Ventures**: up to $10,000
  - https://portal.rumble.cloud/craft-ventures
- **Founders Loft**: 50% off
  - https://f911e387-bf3a-4ed8-9304-fe1c9e5a75b3.filesusr.com/ugd/bf047d_3ae7d127bbe244da9eb2ad9dd6616b79.pdf
- **Fuel Ventures**: 10% off the first year
  - https://www.vestd.com/fuel-ventures-partnership-hub-vestd
- **Inveo Ventures**: up to $2M
  - https://www.inveo.com.tr/media/uwzj0grz/inveoyh_2025q4_en.pdf
- **Keystone Innovation District**: 25% off
  - https://www.keystonedistrict.org/thecofoundry
- **Media Lab Bayern (Medien.Bayern GmbH)**: up to €40,000
  - https://www.media-lab.de/en/offering/media-startup-fellowship/
- **Oregon Innovation Challenge**: up to $10,000
  - https://business.uoregon.edu/hands-on-learning/competitions/oregon-innovation-challenge
- **Replit For Startups**: Up to $25K
  - https://replit.com/startups
- **Sifted**: 10% off
  - https://sifted.eu/sifted-for-startups
- **StartSud Studio**: up to €15,000
  - https://www.startsud.cat/startup-studio/
- **Startup Ice**: 15% off
  - https://startupice.com/benefits/tailor-brands/
- **Startup Norway**: up to $30,000
  - https://marsx.dev/for-startup-accelerators/
- **TheVC Lens**: up to $12k
  - https://thevclens.com/membership
- **Trinet**: 65% off
  - https://www.trinet.com/partners/venture-capital

## How to use this

If you are building a unified perk marketplace, treat each heading above as one SKU and treat the 1,312 CSV rows as **distribution partners / eligibility paths**, not as 1,312 different perks.
