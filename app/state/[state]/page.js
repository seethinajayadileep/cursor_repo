import { rtos, stateGroups, states, getStateSlug } from '@/data/rtos'
import PlateCard from '@/components/PlateCard'
import Link from 'next/link'
import { notFound } from 'next/navigation'

const SITE_URL = 'https://www.rtolookup.site'

export async function generateStaticParams() {
  return states.map(s => ({ state: getStateSlug(s) }))
}

export async function generateMetadata({ params }) {
  const { state: stateSlug } = await params
  const stateName = states.find(s => getStateSlug(s) === stateSlug)
  if (!stateName) return {}

  const rtoList = stateGroups[stateName]
  const codes = rtoList.map(r => r.code).join(', ')
  const title = `${stateName} RTO Codes — All ${rtoList.length} RTOs`
  const desc = `Complete list of all RTO codes in ${stateName}: ${codes}. Find the city and district for each RTO code.`

  return {
    title,
    description: desc,
    alternates: { canonical: `${SITE_URL}/state/${stateSlug}` },
    openGraph: { title, description: desc },
  }
}

export default async function StatePage({ params }) {
  const { state: stateSlug } = await params
  const stateName = states.find(s => getStateSlug(s) === stateSlug)
  if (!stateName) notFound()

  const stateRTOs = stateGroups[stateName]
  const stateCode = stateRTOs[0]?.code.split('-')[0] || ''

  const breadcrumbJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
      { '@type': 'ListItem', position: 2, name: stateName, item: `${SITE_URL}/state/${stateSlug}` },
    ],
  }

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      <section className="state-hero">
        <div className="container">
          <nav className="breadcrumb" aria-label="Breadcrumb">
            <Link href="/">Home</Link>
            <span className="breadcrumb-sep" aria-hidden="true">/</span>
            <span aria-current="page">{stateName}</span>
          </nav>

          <div className="state-hero-inner">
            <div className="state-code-badge" aria-label={`State code: ${stateCode}`}>
              {stateCode}
            </div>
            <div>
              <p className="section-label" style={{ marginBottom: '8px' }}>State RTOs</p>
              <h1 className="section-title">{stateName} RTO Codes</h1>
              <p className="state-intro">
                {stateName} has <strong>{stateRTOs.length} RTO{stateRTOs.length !== 1 ? 's' : ''}</strong> in this database. All vehicles registered in {stateName} carry the <strong>{stateCode}-XX</strong> prefix on their number plates.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">

          <div className="state-rto-grid">
            {stateRTOs.map(rto => <PlateCard key={rto.code} rto={rto} size="md" />)}
          </div>
        </div>
      </section>

      <section className="section state-info-section">
        <div className="container">
          <h2 className="section-title" style={{ marginBottom: '24px' }}>About {stateName} RTOs</h2>
          <div className="prose">
            <p>
              All vehicles registered in {stateName} carry the <strong>{stateCode}</strong> prefix. The two-digit number following {stateCode} identifies the specific district or city RTO where the vehicle was registered. Lower numbers are generally older, more central offices — while higher numbers are newer or outer-district RTOs.
            </p>
            <p>
              To check the registration details or transfer an RC for any {stateCode}-series vehicle, visit the official Parivahan portal or the relevant {stateName} RTO office in person.
            </p>
          </div>
          <div style={{ marginTop: '28px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <a href="https://parivahan.gov.in" target="_blank" rel="noopener noreferrer nofollow" className="btn-outline">Official Parivahan Portal ↗</a>
            <Link href="/guides/rc-transfer" className="btn-outline">RC Transfer Guide</Link>
          </div>
        </div>
      </section>

      <style>{`
        .state-hero {
          padding: 40px 0 56px;
          border-bottom: 1px solid var(--tarmac-border);
        }

        .state-hero-inner {
          display: flex;
          align-items: center;
          gap: 32px;
          margin-top: 28px;
          flex-wrap: wrap;
        }

        .state-code-badge {
          font-family: var(--font-display);
          font-size: clamp(3rem, 8vw, 5rem);
          font-weight: 700;
          color: transparent;
          -webkit-text-stroke: 2px var(--amber);
          text-stroke: 2px var(--amber);
          line-height: 1;
          flex-shrink: 0;
          letter-spacing: 4px;
        }

        /* Light mode: outlined transparent text fails contrast checks,
           so render it as a solid readable fill instead. */
        :root[data-theme="light"] .state-code-badge {
          color: var(--accent-text);
          -webkit-text-stroke: 0;
          text-stroke: 0;
        }

        .state-intro {
          margin-top: 14px;
          font-size: var(--text-base);
          color: var(--text-secondary);
          line-height: 1.7;
          max-width: 500px;
        }

        .state-intro strong { color: var(--text-primary); }

        .state-rto-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }

        @media (min-width: 480px) { .state-rto-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
        @media (min-width: 768px) { .state-rto-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
        @media (min-width: 1024px) { .state-rto-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); } }

        .state-info-section {
          background: var(--tarmac-raised);
          border-top: 1px solid var(--tarmac-border);
        }

        .btn-outline {
          display: inline-flex;
          align-items: center;
          padding: 10px 20px;
          background: transparent;
          color: var(--text-secondary);
          font-size: var(--text-sm);
          font-weight: 600;
          border: 1px solid var(--tarmac-border-2);
          border-radius: var(--r-md);
          transition: border-color 0.15s, color 0.15s;
        }

        .btn-outline:hover {
          border-color: var(--amber-dim);
          color: var(--text-primary);
        }
      `}</style>
    </>
  )
}
