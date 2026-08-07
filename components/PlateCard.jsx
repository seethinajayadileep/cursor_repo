import Link from 'next/link'
import PlateDisplay from './PlateDisplay'

export default function PlateCard({ rto, size = 'sm' }) {
  return (
    <Link href={`/rto/${rto.code.toLowerCase()}`} className="plate-card" aria-label={`${rto.code} – ${rto.city}, ${rto.state}`}>
      <PlateDisplay code={rto.code} size={size} />
      <div className="plate-card-meta">
        <span className="plate-card-city">{rto.city}</span>
        <span className="plate-card-state">{rto.state}</span>
      </div>

      <style>{`
        .plate-card {
          display: flex;
          flex-direction: column;
          gap: 10px;
          padding: 16px;
          background: var(--tarmac-card);
          border: 1px solid var(--tarmac-border);
          border-radius: var(--r-lg);
          transition: border-color 0.18s var(--ease), transform 0.18s var(--ease), box-shadow 0.18s var(--ease);
        }

        .plate-card:hover {
          border-color: var(--amber-dim);
          transform: translateY(-2px);
          box-shadow: var(--shadow-card), 0 0 0 1px rgba(240,160,0,0.1);
        }

        .plate-card:hover .plate {
          border-color: var(--amber);
        }

        .plate-card-meta {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .plate-card-city {
          font-size: var(--text-sm);
          font-weight: 600;
          color: var(--text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .plate-card-state {
          font-size: var(--text-xs);
          color: var(--text-muted);
        }
      `}</style>
    </Link>
  )
}
