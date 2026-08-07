import { guides, getGuide } from '@/data/guides'
import Link from 'next/link'
import { notFound } from 'next/navigation'

const SITE_URL = 'https://www.rtolookup.site'

export async function generateStaticParams() {
  return guides.map(g => ({ slug: g.slug }))
}

export async function generateMetadata({ params }) {
  const { slug } = await params
  const guide = getGuide(slug)
  if (!guide) return {}
  return {
    title: guide.metaTitle,
    description: guide.metaDesc,
    alternates: { canonical: `${SITE_URL}/guides/${slug}` },
    openGraph: { title: guide.metaTitle, description: guide.metaDesc },
  }
}

export default async function GuidePage({ params }) {
  const { slug } = await params
  const guide = getGuide(slug)
  if (!guide) notFound()

  const updatedISO = guide.updated ? `${guide.updated}T00:00:00+05:30` : undefined

  const howToJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'HowTo',
    name: guide.title,
    description: guide.intro,
    ...(updatedISO ? { datePublished: updatedISO, dateModified: updatedISO } : {}),
    step: guide.steps.map((s, i) => ({
      '@type': 'HowToStep',
      position: i + 1,
      name: s.title,
      text: s.body,
    })),
  }

  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: guide.metaTitle || guide.title,
    description: guide.metaDesc || guide.intro,
    ...(updatedISO ? { datePublished: updatedISO, dateModified: updatedISO } : {}),
    inLanguage: 'en-IN',
    author: { '@type': 'Organization', name: 'RTOLookup' },
    publisher: { '@id': `${SITE_URL}/#org` },
    mainEntityOfPage: { '@type': 'WebPage', '@id': `${SITE_URL}/guides/${slug}` },
  }

  const faqJsonLd = guide.faqs?.length ? {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: guide.faqs.map(f => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  } : null

  const breadcrumbJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
      { '@type': 'ListItem', position: 2, name: 'Guides', item: `${SITE_URL}/guides` },
      { '@type': 'ListItem', position: 3, name: guide.title, item: `${SITE_URL}/guides/${slug}` },
    ],
  }

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(howToJsonLd) }} />
      {faqJsonLd && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }} />}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      <article className="guide-page">
        <div className="container">
          <nav className="breadcrumb" aria-label="Breadcrumb" style={{ paddingTop: '32px' }}>
            <Link href="/">Home</Link>
            <span className="breadcrumb-sep" aria-hidden="true">/</span>
            <Link href="/guides">Guides</Link>
            <span className="breadcrumb-sep" aria-hidden="true">/</span>
            <span aria-current="page">{guide.title}</span>
          </nav>

          <div className="guide-layout">
            <div className="guide-main">
              <span className="badge badge-amber" style={{ marginTop: '28px', marginBottom: '16px' }}>{guide.badge}</span>
              <h1 className="guide-h1">{guide.title}</h1>
              {guide.updated && (
                <p className="guide-meta-line">
                  Last updated{' '}
                  <time dateTime={guide.updated}>
                    {new Date(`${guide.updated}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                  </time>
                  {' · '}{guide.steps.length}-step guide
                </p>
              )}
              <p className="guide-intro-text">{guide.intro}</p>

              {guide.quickAnswer && (
                <div className="guide-quick-answer">
                  <p className="quick-answer-label">Quick answer</p>
                  <p className="quick-answer-text">{guide.quickAnswer}</p>
                </div>
              )}

              <h2 className="guide-section-h">Steps</h2>
              <ol className="guide-steps" aria-label="Process steps">
                {guide.steps.map((step, i) => (
                  <li key={i} className="guide-step-item">
                    <div className="guide-step-num" aria-hidden="true">{i + 1}</div>
                    <div className="guide-step-body">
                      <h3 className="guide-step-title">{step.title}</h3>
                      <p className="guide-step-text">{step.body}</p>
                    </div>
                  </li>
                ))}
              </ol>

              {guide.faqs?.length > 0 && (
                <>
                  <h2 className="guide-section-h">Frequently asked questions</h2>
                  <div className="faq-list">
                    {guide.faqs.map((faq, i) => (
                      <details key={i} className="faq-item">
                        <summary className="faq-q">{faq.q}</summary>
                        <p className="faq-a">{faq.a}</p>
                      </details>
                    ))}
                  </div>
                </>
              )}
            </div>

            <aside className="guide-sidebar">
              <div className="sidebar-block">
                <p className="sidebar-label">Official resource</p>
                <a href="https://parivahan.gov.in" target="_blank" rel="noopener noreferrer nofollow" className="sidebar-link">
                  Parivahan Portal ↗
                </a>
                <a href="https://vahan.parivahan.gov.in" target="_blank" rel="noopener noreferrer nofollow" className="sidebar-link">
                  VAHAN Vehicle Search ↗
                </a>
              </div>


              <div className="sidebar-block">
                <p className="sidebar-label">Related guides</p>
                {guides.filter(g => g.slug !== slug).slice(0, 3).map(g => (
                  <Link key={g.slug} href={`/guides/${g.slug}`} className="sidebar-guide-link">
                    {g.title}
                  </Link>
                ))}
              </div>
            </aside>
          </div>
        </div>
      </article>

      <style>{`
        .guide-page { padding-bottom: 80px; }

        .guide-layout {
          display: grid;
          grid-template-columns: 1fr;
          gap: 48px;
          align-items: start;
          margin-top: 8px;
        }

        @media (min-width: 900px) {
          .guide-layout { grid-template-columns: 1fr 300px; }
        }

        .guide-h1 {
          font-family: var(--font-display);
          font-size: clamp(var(--text-2xl), 4vw, var(--text-4xl));
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1.2;
          margin-bottom: 16px;
        }

        .guide-intro-text {
          font-size: var(--text-lg);
          color: var(--text-secondary);
          line-height: 1.7;
          border-left: 3px solid var(--amber);
          padding-left: 20px;
          margin-left: 0;
        }

        .guide-meta-line {
          font-size: var(--text-sm);
          color: var(--text-muted);
          margin-bottom: 16px;
        }

        .guide-quick-answer {
          margin-top: 24px;
          padding: 20px 22px;
          background: var(--amber-glow);
          border: 1px solid rgba(240,160,0,0.3);
          border-radius: var(--r-lg);
        }

        .quick-answer-label {
          font-size: var(--text-xs);
          font-weight: 700;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          color: var(--accent-text);
          margin-bottom: 8px;
        }

        .quick-answer-text {
          font-size: var(--text-base);
          color: var(--text-primary);
          line-height: 1.7;
        }

        .guide-section-h {
          font-family: var(--font-display);
          font-size: var(--text-xl);
          font-weight: 700;
          color: var(--text-primary);
          margin: 40px 0 20px;
          padding-bottom: 10px;
          border-bottom: 1px solid var(--tarmac-border);
        }

        .guide-steps {
          display: flex;
          flex-direction: column;
          gap: 20px;
          list-style: none;
        }

        .guide-step-item {
          display: flex;
          gap: 20px;
          align-items: flex-start;
        }

        .guide-step-num {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: var(--amber-glow);
          border: 1.5px solid rgba(240,160,0,0.4);
          color: var(--accent-text);
          font-family: var(--font-display);
          font-size: var(--text-base);
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .guide-step-body { flex: 1; }

        .guide-step-title {
          font-size: var(--text-base);
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 8px;
        }

        .guide-step-text {
          font-size: var(--text-sm);
          color: var(--text-secondary);
          line-height: 1.75;
        }

        /* FAQ */
        .faq-list { display: flex; flex-direction: column; gap: 8px; }

        .faq-item {
          background: var(--tarmac-card);
          border: 1px solid var(--tarmac-border);
          border-radius: var(--r-md);
          overflow: hidden;
        }

        .faq-item[open] { border-color: var(--tarmac-border-2); }

        .faq-q {
          display: block;
          padding: 16px 18px;
          font-size: var(--text-sm);
          font-weight: 600;
          color: var(--text-primary);
          cursor: pointer;
          list-style: none;
          user-select: none;
        }

        .faq-q::-webkit-details-marker { display: none; }
        .faq-q::after { content: '+'; float: right; color: var(--accent-text); }
        .faq-item[open] .faq-q::after { content: '–'; }
        .faq-q:hover { color: var(--accent-text); }

        .faq-a {
          padding: 0 18px 16px;
          font-size: var(--text-sm);
          color: var(--text-secondary);
          line-height: 1.75;
          border-top: 1px solid var(--tarmac-border);
          padding-top: 14px;
        }

        /* Sidebar */
        .guide-sidebar {
          display: flex;
          flex-direction: column;
          gap: 24px;
          position: sticky;
          top: 80px;
        }

        .sidebar-block {
          background: var(--tarmac-card);
          border: 1px solid var(--tarmac-border);
          border-radius: var(--r-lg);
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .sidebar-label {
          font-size: var(--text-xs);
          font-weight: 700;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 4px;
        }

        .sidebar-link {
          font-size: var(--text-sm);
          color: var(--accent-text);
          text-decoration: underline;
          text-underline-offset: 3px;
        }

        .sidebar-link:hover { color: var(--accent-text); }

        .sidebar-guide-link {
          font-size: var(--text-sm);
          color: var(--text-secondary);
          transition: color 0.12s;
          line-height: 1.5;
        }

        .sidebar-guide-link:hover { color: var(--accent-text); }
      `}</style>
    </>
  )
}
