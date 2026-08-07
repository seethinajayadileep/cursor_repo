import { guides } from '@/data/guides'
import Link from 'next/link'

const SITE_URL = 'https://www.rtolookup.site'

export const metadata = {
  title: 'RTO & Vehicle Guides — RC Transfer, Owner Check & More',
  description: 'Plain-English guides for Indian RTO processes: RC transfer, checking vehicle owner, duplicate RC, NOC, and address change. Forms, fees, and step-by-step instructions.',
  alternates: { canonical: `${SITE_URL}/guides` },
  openGraph: {
    title: 'RTO & Vehicle Guides — RC Transfer, Owner Check & More',
    description: 'Plain-English guides for Indian RTO processes: RC transfer, owner check, duplicate RC, NOC, address change.',
    url: `${SITE_URL}/guides`,
  },
}

export default function GuidesIndex() {
  const itemListJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    itemListElement: guides.map((g, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: g.title,
      url: `${SITE_URL}/guides/${g.slug}`,
    })),
  }

  const breadcrumbJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
      { '@type': 'ListItem', position: 2, name: 'Guides', item: `${SITE_URL}/guides` },
    ],
  }

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListJsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      <section className="guides-hero">
        <div className="container">
          <nav className="breadcrumb" aria-label="Breadcrumb">
            <Link href="/">Home</Link>
            <span className="breadcrumb-sep" aria-hidden="true">/</span>
            <span aria-current="page">Guides</span>
          </nav>
          <p className="section-label" style={{ marginTop: '28px' }}>Step-by-step</p>
          <h1 className="section-title">RTO & Vehicle Guides</h1>
          <p className="guides-hero-sub">
            Every RTO process explained in plain English — the forms you need, what they cost, and exactly what to do at each step.
          </p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="guides-index-grid">
            {guides.map(guide => (
              <Link key={guide.slug} href={`/guides/${guide.slug}`} className="guide-index-card">
                <span className="badge badge-amber guide-index-badge">{guide.badge}</span>
                <h2 className="guide-index-title">{guide.title}</h2>
                <p className="guide-index-desc">{guide.intro}</p>
                <span className="guide-index-cta">Read guide →</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <style>{`
        .guides-hero {
          padding: 40px 0 48px;
          border-bottom: 1px solid var(--tarmac-border);
          background: radial-gradient(ellipse 70% 60% at 50% 0%, rgba(26,60,138,0.07) 0%, transparent 70%);
        }

        .guides-hero-sub {
          font-size: var(--text-lg);
          color: var(--text-secondary);
          line-height: 1.65;
          max-width: 560px;
          margin-top: 14px;
        }

        .guides-index-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 16px;
        }

        @media (min-width: 640px) { .guides-index-grid { grid-template-columns: repeat(2, 1fr); } }

        .guide-index-card {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 28px;
          background: var(--tarmac-card);
          border: 1px solid var(--tarmac-border);
          border-radius: var(--r-lg);
          transition: border-color 0.18s, transform 0.18s var(--ease);
        }

        .guide-index-card:hover {
          border-color: var(--amber-dim);
          transform: translateY(-2px);
        }

        .guide-index-badge { align-self: flex-start; }

        .guide-index-title {
          font-family: var(--font-display);
          font-size: var(--text-xl);
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1.25;
        }

        .guide-index-desc {
          font-size: var(--text-sm);
          color: var(--text-secondary);
          line-height: 1.65;
          flex: 1;
        }

        .guide-index-cta {
          font-size: var(--text-sm);
          font-weight: 600;
          color: var(--accent-text);
        }
      `}</style>
    </>
  )
}
