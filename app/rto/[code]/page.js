import { rtos, getRTO, getSiblings } from '@/data/rtos'
import PlateDisplay from '@/components/PlateDisplay'
import PlateCard from '@/components/PlateCard'
import Link from 'next/link'
import { notFound } from 'next/navigation'

const SITE_URL = 'https://www.rtolookup.site'

export async function generateStaticParams() {
  return rtos.map(r => ({ code: r.code.toLowerCase() }))
}

export async function generateMetadata({ params }) {
  const { code } = await params
  const rto = getRTO(code)
  if (!rto) return {}

  const title = `${rto.code} RTO – ${rto.city}, ${rto.state}`
  const desc = `${rto.code} is the RTO code for ${rto.city} in ${rto.state}. Find office details, jurisdiction, vehicle registration info, and related RTO codes.`

  return {
    title,
    description: desc,
    alternates: { canonical: `${SITE_URL}/rto/${rto.code.toLowerCase()}` },
    openGraph: { title, description: desc, url: `${SITE_URL}/rto/${rto.code.toLowerCase()}` },
  }
}

export default async function RTOPage({ params }) {
  const { code } = await params
  const rto = getRTO(code)
  if (!rto) notFound()

  const siblings = getSiblings(rto)
  const [statePrefix, distNum] = rto.code.split('-')

  const breadcrumbJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
      { '@type': 'ListItem', position: 2, name: rto.state, item: `${SITE_URL}/state/${rto.state.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}` },
      { '@type': 'ListItem', position: 3, name: rto.code, item: `${SITE_URL}/rto/${rto.code.toLowerCase()}` },
    ],
  }

  const faqJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: `What does ${rto.code} mean on a number plate?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: `${rto.code} is the RTO code for ${rto.city} in ${rto.state}. The prefix "${statePrefix}" stands for ${rto.state}, and "${distNum}" is the district code assigned to ${rto.district}.`,
        },
      },
      {
        '@type': 'Question',
        name: `Which area does ${rto.code} cover?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: `${rto.code} covers the ${rto.district} district in ${rto.state}. The office handles vehicle registrations, RC transfers, and driving licences for this jurisdiction.`,
        },
      },
      {
        '@type': 'Question',
        name: `How do I transfer an RC for a ${rto.code} vehicle?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: `To transfer an RC for a vehicle registered under ${rto.code} (${rto.city}), visit the ${rto.city} RTO or use the Parivahan portal at parivahan.gov.in. You will need Form 29, Form 30, the original RC, insurance, PUC certificate, and the appropriate transfer fee.`,
        },
      },
      {
        '@type': 'Question',
        name: `Is a vehicle from ${rto.code} registered in ${rto.state}?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: `Yes. Any vehicle with a number plate starting with "${rto.code}" was registered at the ${rto.city} Regional Transport Office in ${rto.state}.`,
        },
      },
    ],
  }

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }} />

      {/* ── Hero ── */}
      <section className="rto-hero">
        <div className="container">
          <nav className="breadcrumb" aria-label="Breadcrumb">
            <Link href="/">Home</Link>
            <span className="breadcrumb-sep" aria-hidden="true">/</span>
            <Link href={`/state/${rto.state.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}`}>{rto.state}</Link>
            <span className="breadcrumb-sep" aria-hidden="true">/</span>
            <span aria-current="page">{rto.code}</span>
          </nav>

          <div className="rto-hero-inner">
            <div className="rto-hero-left">
              <PlateDisplay code={rto.code} size="xl" />
              <div className="rto-decode">
                <div className="rto-decode-item">
                  <span className="decode-label">State code</span>
                  <span className="decode-value mono">{statePrefix}</span>
                  <span className="decode-meaning">{rto.state}</span>
                </div>
                <span className="decode-sep" aria-hidden="true">–</span>
                <div className="rto-decode-item">
                  <span className="decode-label">District</span>
                  <span className="decode-value mono">{distNum}</span>
                  <span className="decode-meaning">{rto.district}</span>
                </div>
              </div>
            </div>

            <div className="rto-hero-right">
              <div className="badge badge-blue" style={{ marginBottom: '12px' }}>{rto.type} RTO</div>
              <h1 className="rto-title">{rto.code} — {rto.city}</h1>
              <p className="rto-intro">
                <strong>{rto.code}</strong> is the Regional Transport Office code for <strong>{rto.city}</strong>, located in the <strong>{rto.district}</strong> district of <strong>{rto.state}</strong>. Any vehicle with a number plate beginning with {rto.code} was registered at this RTO.
              </p>

              <div className="rto-spec-grid">
                {[
                  { label: 'State', value: rto.state },
                  { label: 'City / Office', value: rto.city },
                  { label: 'District', value: rto.district },
                  { label: 'Zone', value: rto.zone },
                  { label: 'Type', value: rto.type },
                  { label: 'State Code', value: statePrefix },
                ].map(({ label, value }) => (
                  <div key={label} className="spec-item">
                    <span className="spec-label">{label}</span>
                    <span className="spec-value">{value}</span>
                  </div>
                ))}
              </div>

              <div className="rto-actions">
                <a href="https://vahan.parivahan.gov.in/vahanservice/vahan/ui/appl_status/form_Know_Appl_Status.xhtml" target="_blank" rel="noopener noreferrer nofollow" className="btn-primary">
                  Check RC Status ↗
                </a>
                <Link href="/guides/rc-transfer" className="btn-ghost">
                  RC Transfer Guide
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* ── FAQ ── */}
      <section className="section">
        <div className="container">
          <p className="section-label">Common questions</p>
          <h2 className="section-title" style={{ marginBottom: '32px' }}>About {rto.code}</h2>
          <div className="faq-list">
            {[
              {
                q: `What does ${rto.code} mean on a number plate?`,
                a: `${rto.code} is the RTO code for ${rto.city} in ${rto.state}. The "${statePrefix}" prefix identifies ${rto.state}, and "${distNum}" is the district number assigned to ${rto.district}. Together they uniquely identify the ${rto.city} Regional Transport Office.`,
              },
              {
                q: `Which area does ${rto.code} cover?`,
                a: `${rto.code} covers ${rto.district} district in ${rto.state}. The RTO office handles all vehicle registrations, RC transfers, fitness certificates, and driving licences for this jurisdiction.`,
              },
              {
                q: `How do I transfer an RC for a ${rto.code} vehicle?`,
                a: `For a vehicle registered under ${rto.code} (${rto.city}), you can either visit the ${rto.city} RTO in person or use the Parivahan online portal. You'll need Form 29 (notice of transfer), Form 30 (application for transfer), the original RC book, valid insurance, PUC certificate, and the transfer fee (varies by vehicle type). The transfer typically takes 7–30 working days.`,
              },
              {
                q: `How do I find the owner of a ${rto.code} registered vehicle?`,
                a: `You can check the registered owner of any ${rto.code} vehicle on the Parivahan VAHAN portal using the vehicle registration number. Enter the full number (e.g., ${rto.code} AB 1234) and select "Know Your Vehicle Details" — this shows the owner's name, registration date, and insurance status.`,
              },
            ].map((item, i) => (
              <details key={i} className="faq-item">
                <summary className="faq-q">{item.q}</summary>
                <p className="faq-a">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── Siblings ── */}
      {siblings.length > 0 && (
        <section className="section sibling-section">
          <div className="container">
            <p className="section-label">Other RTOs in {rto.state}</p>
            <h2 className="section-title" style={{ marginBottom: '28px' }}>Related RTO codes</h2>
            <div className="sibling-grid">
              {siblings.map(s => <PlateCard key={s.code} rto={s} size="sm" />)}
            </div>
          </div>
        </section>
      )}

      <style>{`
        .rto-hero {
          padding: 40px 0 56px;
          border-bottom: 1px solid var(--tarmac-border);
        }

        .rto-hero-inner {
          display: grid;
          grid-template-columns: 1fr;
          gap: 48px;
          margin-top: 32px;
          align-items: start;
        }

        @media (min-width: 768px) {
          .rto-hero-inner { grid-template-columns: auto 1fr; }
        }

        .rto-hero-left {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .rto-decode {
          display: flex;
          align-items: center;
          gap: 16px;
          background: var(--tarmac-raised);
          border: 1px solid var(--tarmac-border);
          border-radius: var(--r-md);
          padding: 14px 20px;
        }

        .rto-decode-item {
          display: flex;
          flex-direction: column;
          gap: 3px;
        }

        .decode-label {
          font-size: var(--text-xs);
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .decode-value {
          font-family: var(--font-mono);
          font-size: var(--text-2xl);
          font-weight: 700;
          color: var(--accent-text);
        }

        .decode-meaning {
          font-size: var(--text-xs);
          color: var(--text-secondary);
        }

        .decode-sep {
          font-size: var(--text-2xl);
          color: var(--tarmac-border-2);
          align-self: flex-end;
          padding-bottom: 6px;
        }

        .mono { font-family: var(--font-mono); }

        .rto-title {
          font-family: var(--font-display);
          font-size: clamp(var(--text-2xl), 4vw, var(--text-4xl));
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1.2;
          margin-bottom: 14px;
        }

        .rto-intro {
          font-size: var(--text-base);
          color: var(--text-secondary);
          line-height: 1.7;
          margin-bottom: 28px;
        }

        .rto-intro strong { color: var(--text-primary); }

        .rto-spec-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 1px;
          background: var(--tarmac-border);
          border: 1px solid var(--tarmac-border);
          border-radius: var(--r-md);
          overflow: hidden;
          margin-bottom: 28px;
        }

        @media (min-width: 480px) {
          .rto-spec-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }

        .spec-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 14px 16px;
          background: var(--tarmac-card);
        }

        .spec-label {
          font-size: var(--text-xs);
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.8px;
        }

        .spec-value {
          font-size: var(--text-sm);
          font-weight: 600;
          color: var(--text-primary);
        }

        .rto-actions {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        /* FAQ */
        .faq-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-width: 760px;
        }

        .faq-item {
          background: var(--tarmac-card);
          border: 1px solid var(--tarmac-border);
          border-radius: var(--r-md);
          overflow: hidden;
        }

        .faq-item[open] { border-color: var(--tarmac-border-2); }

        .faq-q {
          display: block;
          padding: 18px 20px;
          font-size: var(--text-base);
          font-weight: 600;
          color: var(--text-primary);
          cursor: pointer;
          list-style: none;
          user-select: none;
          transition: color 0.12s;
        }

        .faq-q::-webkit-details-marker { display: none; }
        .faq-q::after { content: '+'; float: right; color: var(--accent-text); font-family: var(--font-mono); }
        .faq-item[open] .faq-q::after { content: '–'; }
        .faq-q:hover { color: var(--accent-text); }

        .faq-a {
          padding: 0 20px 18px;
          font-size: var(--text-sm);
          color: var(--text-secondary);
          line-height: 1.75;
          border-top: 1px solid var(--tarmac-border);
          padding-top: 14px;
        }

        /* Siblings */
        .sibling-section {
          background: var(--tarmac-raised);
          border-top: 1px solid var(--tarmac-border);
        }

        .sibling-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        @media (min-width: 480px) { .sibling-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
        @media (min-width: 768px) { .sibling-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); } }
      `}</style>
    </>
  )
}
