import Link from 'next/link'
import PlateDisplay from '@/components/PlateDisplay'

export const metadata = {
  title: '404 — Page Not Found',
  description: 'The RTO code or page you looked for doesn\'t exist in our database.',
  robots: { index: false, follow: true },
}

export default function NotFound() {
  return (
    <div className="nf-wrap">
      <div className="container nf-inner">
        <div aria-hidden="true" style={{ opacity: 0.3 }}>
          <PlateDisplay code="404" size="xl" />
        </div>
        <h1 className="nf-title">Page not found</h1>
        <p className="nf-body">
          That RTO code or page isn't in our database. Try searching for a valid code like <strong>MH-01</strong> or <strong>DL-4</strong>.
        </p>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
          <Link href="/" className="btn-primary">Search RTO codes</Link>
          <Link href="/guides/rc-transfer" className="btn-ghost">View guides</Link>
        </div>
      </div>

      <style>{`
        .nf-wrap {
          min-height: 60vh;
          display: flex;
          align-items: center;
          padding: 64px 0;
        }

        .nf-inner {
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
        }

        .nf-title {
          font-family: var(--font-display);
          font-size: var(--text-3xl);
          font-weight: 700;
          color: var(--text-primary);
        }

        .nf-body {
          font-size: var(--text-base);
          color: var(--text-secondary);
          max-width: 400px;
          line-height: 1.65;
        }

        .nf-body strong {
          font-family: var(--font-mono);
          color: var(--text-primary);
          font-size: 0.9em;
        }
      `}</style>
    </div>
  )
}
