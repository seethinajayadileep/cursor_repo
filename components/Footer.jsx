import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand">
            <p className="footer-logo">RTOLookup</p>
            <p className="footer-tagline">Plain-English explanations of Indian vehicle registration, RC transfers, and RTO processes.</p>
            <p className="footer-disclaimer">Not affiliated with MoRTH or Parivahan. For official services visit <a href="https://parivahan.gov.in" target="_blank" rel="noopener noreferrer nofollow">parivahan.gov.in</a></p>
          </div>

          <div className="footer-links">
            <p className="footer-links-title">Popular States</p>
            <ul>
              <li><Link href="/state/maharashtra">Maharashtra RTOs</Link></li>
              <li><Link href="/state/delhi">Delhi RTOs</Link></li>
              <li><Link href="/state/karnataka">Karnataka RTOs</Link></li>
              <li><Link href="/state/tamil-nadu">Tamil Nadu RTOs</Link></li>
              <li><Link href="/state/gujarat">Gujarat RTOs</Link></li>
              <li><Link href="/state/uttar-pradesh">Uttar Pradesh RTOs</Link></li>
            </ul>
          </div>

          <div className="footer-links">
            <p className="footer-links-title">Guides</p>
            <ul>
              <li><Link href="/guides/rc-transfer">RC Transfer Guide</Link></li>
              <li><Link href="/guides/check-vehicle-owner">Check Vehicle Owner</Link></li>
              <li><Link href="/guides/duplicate-rc">Duplicate RC</Link></li>
              <li><Link href="/guides/address-change">Address Change in RC</Link></li>
              <li><Link href="/guides/noc">NOC for Vehicle</Link></li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <p>© {new Date().getFullYear()} RTOLookup. Information is for reference only.</p>
        </div>
      </div>

      <style>{`
        .site-footer {
          border-top: 1px solid var(--tarmac-border);
          padding: 48px 0 24px;
          margin-top: 80px;
        }

        .footer-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 40px;
          margin-bottom: 40px;
        }

        @media (min-width: 640px) {
          .footer-grid { grid-template-columns: 2fr 1fr 1fr; gap: 48px; }
        }

        .footer-logo {
          font-family: var(--font-display);
          font-size: var(--text-xl);
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 10px;
          letter-spacing: 1px;
        }

        .footer-tagline {
          font-size: var(--text-sm);
          color: var(--text-secondary);
          line-height: 1.6;
          margin-bottom: 12px;
          max-width: 320px;
        }

        .footer-disclaimer {
          font-size: var(--text-xs);
          color: var(--text-muted);
          line-height: 1.6;
          max-width: 320px;
        }

        .footer-disclaimer a {
          color: var(--accent-text);
          text-decoration: underline;
        }

        .footer-links-title {
          font-size: var(--text-xs);
          font-weight: 700;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 14px;
        }

        .footer-links ul {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .footer-links a {
          font-size: var(--text-sm);
          color: var(--text-secondary);
          transition: color 0.12s;
        }

        .footer-links a:hover { color: var(--accent-text); }

        .footer-bottom {
          border-top: 1px solid var(--tarmac-border);
          padding-top: 20px;
          font-size: var(--text-xs);
          color: var(--text-muted);
        }
      `}</style>
    </footer>
  )
}
